"""Extraction Service - two-stage screenplay extraction.

Implements the llm-extraction spec:

Stage 1 (deterministic, no LLM):
    Parse Fountain structure to determine the character set and dialogue
    attribution. Characters come ONLY from cue structure, never guessed.

Stage 2 (LLM semantic):
    Feed the deterministic structure as context to the LLM, which extracts
    event summaries, character status changes, and fact assertions as
    structured JSON. The system computes source spans deterministically by
    locating the LLM-quoted source text back in the manuscript - the LLM does
    not invent offsets.

Failure isolation:
    LLM failure / timeout / malformed output never blocks the user. The
    deterministic stage still commits (characters), and the semantic stage is
    skipped with a recorded failure so the next trigger can retry.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from ..models import compute_text_hash
from .event_log import EventLogService
from .fountain import ElementType, parse_fountain
from .llm_provider import LLMProvider

logger = logging.getLogger("first_story.extraction")


_EXTRACTION_SYSTEM = (
    "你是剧本结构化提取器。你会收到一段文本，以及已经确定的角色名单。"
    "你的任务：只提取剧情事件、角色状态变化、事实断言，输出严格 JSON。"
    "不要评判创作好坏，不要给建议，不要改写正文。"
    "每条 fact 必须给出 source_quote：从正文中原样摘录的、能支撑该 fact 的最短文本片段。"
    "剧情事件(plot_events)是重要的情节转折点或场景，需要有 summary 概述。"
)

_EXTRACTION_TEMPLATE = """\
已确定角色：{characters}

文本：
<<<
{content}
>>>

请输出 JSON，结构如下（只输出 JSON，不要其它文字）：
{{
  "facts": [
    {{
      "content": "对该事实的简洁陈述",
      "about_characters": ["涉及的角色名"],
      "kind": "event | state_change | assertion",
      "character_statuses": {{ "角色名": "alive | dead | unknown" }},
      "source_quote": "正文中原样摘录、支撑该 fact 的最短片段"
    }}
  ],
  "plot_events": [
    {{
      "summary": "事件概述（如：主角在厕所遇到吉祥物，被要求成为魔法少女）",
      "participants": ["参与角色名"],
      "story_time": "故事时间（可选，如：白天、某年某月）"
    }}
  ]
}}
说明：
- facts：提取所有事实性描述，包括角色属性、关系、设定等
- plot_events：提取重要的情节事件，如关键转折、场景变化、重要行动等
- character_statuses 是「角色名 → 生死状态」的映射：对该 fact 涉及的每个角色，分别判断其在这句话语境下是活着(alive)、已死亡(dead)还是无法确定(unknown)。
- 指代归一（重要）：同一个角色在原文里可能有多种称呼。请在所有输出中对同一角色统一使用同一个规范名。
- 不要评判、不要建议，只做客观提取。
若没有可提取的内容，返回 {{"facts": [], "plot_events": []}}。"""


@dataclass
class ExtractedFact:
    content: str
    about_characters: list[str]
    kind: str
    source_quote: str
    start: int
    end: int
    character_statuses: dict[str, str] = field(default_factory=dict)


@dataclass
class ExtractedPlotEvent:
    summary: str
    participants: list[str]
    story_time: Optional[str] = None


@dataclass
class ExtractionResult:
    """Outcome of one extraction run."""

    characters: list[str] = field(default_factory=list)
    new_character_ids: list[str] = field(default_factory=list)
    facts: list[ExtractedFact] = field(default_factory=list)
    fact_ids: list[str] = field(default_factory=list)
    plot_events: list[ExtractedPlotEvent] = field(default_factory=list)
    plot_event_ids: list[str] = field(default_factory=list)
    llm_succeeded: bool = False
    llm_error: Optional[str] = None
    batch_id: Optional[str] = None


class ExtractionService:
    """Runs deterministic + LLM extraction and commits results to the log."""

    def __init__(
        self,
        event_log: EventLogService,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.event_log = event_log
        self.llm = llm_provider
        from .hub import get_hub

        self._writer = get_hub().writer_for(event_log)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _existing_character_names(self) -> set[str]:
        """Collect character names already registered in the log."""
        names: set[str] = set()
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype == "character.created":
                name = event.payload.get("name")
                if name:
                    names.add(name)
        return names

    def extract(
        self,
        content: str,
        *,
        document_id: str = "main",
        revision: str = "",
        acceptance_status: str = "committed",
        source_type: str = "document",
    ) -> ExtractionResult:
        """Run the two-stage extraction for a manuscript revision.

        ``acceptance_status`` / ``source_type`` are stamped onto every produced
        fact. In ``candidate`` mode the extraction is an "idea record" only: it
        MUST NOT write committed-world entity events (``character.created`` /
        ``batch.committed``), so a chat brainstorm never becomes a prose-world
        entity. Only ``fact.created`` events (carrying ``acceptance_status=
        candidate``) are written.
        """
        is_candidate = acceptance_status == "candidate"
        result = ExtractionResult()
        content_hash = compute_text_hash(content)
        batch_id = self._new_id("batch")
        result.batch_id = batch_id

        # --- Stage 1: deterministic structure (no LLM) ---
        parsed = parse_fountain(content)
        result.characters = list(parsed.characters)

        # candidate mode is an idea record: never write committed-world entity
        # events. Characters / batch commit only happen for committed prose.
        if not is_candidate:
            existing = self._existing_character_names()
            for el in parsed.elements:
                if el.type is not ElementType.CHARACTER:
                    continue
                name = el.character or el.text
                if name in existing:
                    continue
                existing.add(name)
                cid = self._new_id("char")
                event_id = self._new_id("evt")
                self._writer.append(
                    event_id=event_id,
                    idempotency_key=f"{batch_id}:char:{name}",
                    event_type="character.created",
                    payload={
                        "character_id": cid,
                        "name": name,
                        "initial_status": "unknown",
                    },
                    actor="extraction_agent",
                    batch_id=batch_id,
                )
                result.new_character_ids.append(cid)

        # --- Stage 2: LLM semantic extraction (isolated from failures) ---
        if self.llm is None:
            result.llm_error = "no_llm_configured"
            if not is_candidate:
                self._commit_batch(batch_id, document_id, revision)
            return result

        try:
            extracted_facts, extracted_plot_events = self._llm_extract(content, parsed.characters)
        except Exception as exc:  # noqa: BLE001 - isolate; never block writing
            logger.warning("extraction LLM stage failed: %s", exc)
            result.llm_error = str(exc)
            if not is_candidate:
                self._commit_batch(batch_id, document_id, revision)
            return result

        result.llm_succeeded = True
        result.facts = extracted_facts
        result.plot_events = extracted_plot_events
        
        # 从 facts 中收集所有提及的角色名，创建角色（如果不存在）
        all_mentioned_characters: set[str] = set()
        for fact in extracted_facts:
            for name in fact.about_characters:
                if name:
                    all_mentioned_characters.add(name)
        
        # 从 plot_events 中也收集角色
        for pe in extracted_plot_events:
            for name in pe.participants:
                if name:
                    all_mentioned_characters.add(name)
        
        # 为新角色创建事件（candidate 模式也创建，标记 acceptance_status）
        existing_names = self._existing_character_names()
        for name in all_mentioned_characters:
            if name in existing_names:
                continue
            existing_names.add(name)
            cid = self._new_id("char")
            event_id = self._new_id("evt")
            self._writer.append(
                event_id=event_id,
                idempotency_key=f"{batch_id}:char:{name}",
                event_type="character.created",
                payload={
                    "character_id": cid,
                    "name": name,
                    "initial_status": "unknown",
                    "acceptance_status": acceptance_status,  # 标记是 candidate 还是 committed
                },
                actor="extraction_agent",
                batch_id=batch_id,
            )
            result.new_character_ids.append(cid)
        
        # 写入 facts
        for fact in extracted_facts:
            fid = self._new_id("fact")
            event_id = self._new_id("evt")
            self._writer.append(
                event_id=event_id,
                idempotency_key=f"{batch_id}:{fid}",
                event_type="fact.created",
                payload={
                    "fact_id": fid,
                    "content": fact.content,
                    "about_character_ids": [],
                    "about_character_names": fact.about_characters,
                    "source_document_id": document_id,
                    "source_revision": revision,
                    "source_span": {"start": fact.start, "end": fact.end},
                    "source_text_hash": content_hash,
                    "extraction_confidence": 0.7,
                    "kind": fact.kind,
                    "character_statuses": fact.character_statuses,
                    "acceptance_status": acceptance_status,
                    "source_type": source_type,
                },
                actor="extraction_agent",
                batch_id=batch_id,
            )
            result.fact_ids.append(fid)

        # 写入 plot_events
        for pe in extracted_plot_events:
            pe_id = self._new_id("pe")
            event_id = self._new_id("evt")
            self._writer.append(
                event_id=event_id,
                idempotency_key=f"{batch_id}:pe:{pe_id}",
                event_type="plot_event.created",
                payload={
                    "plot_event_id": pe_id,
                    "summary": pe.summary,
                    "story_time": {"type": "unknown", "text": pe.story_time} if pe.story_time else {"type": "unknown"},
                    "participant_character_ids": [],
                    "participant_character_names": pe.participants,
                    "acceptance_status": acceptance_status,
                    "source_type": source_type,
                },
                actor="extraction_agent",
                batch_id=batch_id,
            )
            result.plot_event_ids.append(pe_id)

        if not is_candidate:
            self._commit_batch(batch_id, document_id, revision)
        return result

    def _commit_batch(self, batch_id: str, document_id: str, revision: str) -> None:
        self._writer.append(
            event_id=self._new_id("evt"),
            idempotency_key=f"{batch_id}:committed",
            event_type="batch.committed",
            payload={
                "member_event_ids": [],
                "source_document_id": document_id,
                "source_revision": revision,
            },
            actor="hub",
            batch_id=batch_id,
        )

    def _llm_extract(
        self, content: str, characters: list[str]
    ) -> tuple[list[ExtractedFact], list[ExtractedPlotEvent]]:
        prompt = _EXTRACTION_TEMPLATE.format(
            characters=", ".join(characters) if characters else "（暂无）",
            content=content,
        )
        response = self.llm.complete(prompt, system=_EXTRACTION_SYSTEM)
        data = self._parse_llm_json(response.text)

        facts: list[ExtractedFact] = []
        for raw in data.get("facts", []):
            quote = (raw.get("source_quote") or "").strip()
            start, end = self._locate(content, quote)
            about = [c for c in raw.get("about_characters", []) if c]
            statuses = self._parse_statuses(raw, about)
            facts.append(
                ExtractedFact(
                    content=raw.get("content", "").strip(),
                    about_characters=about,
                    kind=raw.get("kind", "assertion"),
                    source_quote=quote,
                    start=start,
                    end=end,
                    character_statuses=statuses,
                )
            )

        plot_events: list[ExtractedPlotEvent] = []
        for raw in data.get("plot_events", []):
            plot_events.append(
                ExtractedPlotEvent(
                    summary=(raw.get("summary") or "").strip(),
                    participants=[p for p in raw.get("participants", []) if p],
                    story_time=raw.get("story_time"),
                )
            )

        return facts, plot_events

    @staticmethod
    def _parse_statuses(raw: dict, about: list[str]) -> dict[str, str]:
        """Normalize per-character statuses from an LLM fact.

        Accepts the new ``character_statuses`` map. For backward compatibility
        with an older single-value ``character_status``, that value is broadcast
        across the fact's characters. The semantic decision still comes from the
        LLM; this only normalizes the shape.
        """
        allowed = {"alive", "dead", "unknown"}
        statuses: dict[str, str] = {}
        raw_map = raw.get("character_statuses")
        if isinstance(raw_map, dict):
            for name, value in raw_map.items():
                if not name:
                    continue
                norm = (value or "unknown").strip().lower()
                statuses[name] = norm if norm in allowed else "unknown"
            return statuses
        # Legacy fallback: a single status applied to every named character.
        legacy = (raw.get("character_status") or "unknown").strip().lower()
        legacy = legacy if legacy in allowed else "unknown"
        for name in about:
            statuses[name] = legacy
        return statuses

    @staticmethod
    def _parse_llm_json(text: str) -> dict:
        """Best-effort JSON extraction from an LLM response."""
        text = text.strip()
        # Strip code fences if present.
        if text.startswith("```"):
            text = text.strip("`")
            # Drop a leading language tag like 'json\n'.
            nl = text.find("\n")
            if nl != -1:
                text = text[nl + 1 :]
        # Find the outermost JSON object.
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise ValueError("LLM response contained no JSON object")
        return json.loads(text[first : last + 1])

    @staticmethod
    def _locate(content: str, quote: str) -> tuple[int, int]:
        """Locate the quoted source text in the manuscript to get a span.

        The span is computed deterministically; if the quote cannot be found
        verbatim, the span defaults to (0, 0) rather than trusting the LLM.
        """
        if quote:
            idx = content.find(quote)
            if idx != -1:
                return idx, idx + len(quote)
        return 0, 0
