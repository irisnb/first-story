"""Alias Resolution Service - identity-only coreference normalization.

This service exists to solve the "soul function" failure mode discovered during
real-LLM acceptance: the benchmark contradiction (a sister who died, then phones
home) only registers as a conflict when the system recognizes that the several
surface names for that person ("姐姐", "姐", "已故姐姐", ...) refer to ONE
character. When that judgment was folded into the extraction LLM call, the model
preferred to "make the story consistent" - it split the person into a dead one
and a living one, dissolving the contradiction on its own.

Design (per Oracle review, recorded in AGENTS.md decision log):

- IDENTITY ONLY. This pass decides *who is who*. It NEVER decides alive/dead.
  Status remains the extraction LLM's per-fact judgment; the contradiction
  detector still does the deterministic alive-vs-dead comparison.
- CONSERVATIVE. A wrong *merge* fabricates a phantom contradiction (or erases a
  real one) - far worse than a missed merge, which only leaves a known gap. So
  the prompt is instructed to bind names only when context makes co-reference
  clear, and to leave anything ambiguous unbound (its own canonical name).
- APPEND-ONLY. Each run emits ``character.alias_bound`` events. The alias map is
  rebuilt by replaying them; later runs extend the map but never delete bindings.
- FAILURE-ISOLATED. Like extraction, any LLM failure here is swallowed: no alias
  bindings are written, the detector simply falls back to exact-name grouping.

The detector consumes the replayed alias map to normalize fact character names
to their canonical form BEFORE grouping - a table lookup, never a re-guess of
meaning from keywords (which is the forbidden failure mode).
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .event_log import EventLogService
from .llm_provider import LLMProvider

logger = logging.getLogger("first_story.alias")


_ALIAS_SYSTEM = (
    "你是剧本角色身份归一器。你只判断「哪些称呼指向同一个角色」，"
    "绝不判断角色的生死、状态或剧情。你只关心身份，不关心其它任何事。"
    "宁可漏判，也绝不把两个不同的人错并成一个——错并会凭空制造或抹掉矛盾，"
    "比漏判严重得多。只在上下文足以确认是同一人时才归并；任何模糊、不确定的，"
    "一律各自独立，不要归并。"
)

_ALIAS_TEMPLATE = """\
下面是从同一篇剧本里提取出的、出现过的角色称呼（可能含全名、简称、昵称、亲属称谓）：
{names}

这些称呼里，有些可能指向同一个角色（例如「姐姐」「姐」「林晚」在上下文里是同一人）。
请基于下面的正文判断哪些称呼是同一个人。

正文：
<<<
{content}
>>>

只输出 JSON，不要任何其它文字，结构如下：
{{
  "groups": [
    {{
      "canonical": "该角色的规范名（从下列称呼里挑最完整、最明确的一个）",
      "aliases": ["指向同一角色的其它称呼", "..."]
    }}
  ]
}}
铁律：
- 你只做身份归并，绝不输出、绝不考虑任何生死/状态信息。
- 亲属称谓的唯一性属于身份判断（不是生死判断）：像「妈妈」「姐姐」「哥哥」「爸爸」这类亲属称谓，若正文里没有明确证据表明存在多个不同的同类亲属（例如没有写出「大姐」「二姐」之分），就应视为同一个角色——即使这些称呼带有修饰词（如「已故的姐姐」「在世的姐姐」「姐姐（已故）」），也仍是同一个人，必须归并到一起。修饰词描述的是状态，不改变身份。
- 亲属称谓的简称与全称是同一人：「姐」与「姐姐」、「妈」与「妈妈」、「哥」与「哥哥」在同一篇正文里若无明确区分，就是同一个角色，必须归并。
- 除亲属称谓外，只在上下文明确支持时才归并；不确定的称呼保持独立。
- canonical 必须是上面给出的称呼之一；aliases 里的每个名字也必须来自上面的称呼。
- 不要造出列表里没有的新名字。
- 若没有任何可确认的同一人归并，返回 {{"groups": []}}。

示例（仅示范格式与归并粒度，与你要处理的正文无关）：
称呼：阿明, 哥哥, 哥, 远行的哥哥
正文里某人提到离家多年的哥哥，又在见面时直接喊「哥」。
正确输出：{{"groups": [{{"canonical": "哥哥", "aliases": ["哥", "远行的哥哥"]}}]}}
（说明：哥哥/哥/远行的哥哥都指同一个唯一的哥哥，归为一人；说话者本人是另一个人，不与哥哥归并。注意这里完全没有判断任何生死或状态。）"""


@dataclass
class AliasGroup:
    """One resolved identity cluster: canonical name + its aliases."""

    canonical: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class AliasResolutionResult:
    """Outcome of one alias resolution run."""

    groups: list[AliasGroup] = field(default_factory=list)
    bound_event_ids: list[str] = field(default_factory=list)
    llm_succeeded: bool = False
    llm_error: Optional[str] = None


class AliasResolverService:
    """Resolves character coreference into an append-only alias map."""

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

    # ------------------------------------------------------------------ read

    def load_alias_map(self) -> dict[str, str]:
        """Replay alias-bound events into a {surface_name -> canonical} map.

        Append-only semantics: bindings accumulate. If two runs disagree, the
        later binding wins for that surface name (a conservative last-write
        policy; bindings are never deleted, only superseded).
        """
        mapping: dict[str, str] = {}
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "character.alias_bound":
                continue
            p = event.payload
            canonical = p.get("canonical_name")
            if not canonical:
                continue
            for alias in p.get("aliases", []):
                if alias:
                    mapping[alias] = canonical
            # The canonical name maps to itself for uniform downstream lookup.
            mapping.setdefault(canonical, canonical)
        return mapping

    @staticmethod
    def canonicalize(name: str, alias_map: dict[str, str]) -> str:
        """Return the canonical name for a surface name (identity if unknown)."""
        return alias_map.get(name, name)

    def _fact_names(self) -> list[str]:
        """Collect every distinct character name appearing in committed facts.

        These include names the extraction LLM may have invented (e.g. it split
        a person into '已故姐姐' and '在世姐姐'); resolving those back together is
        exactly the job here.
        """
        names: list[str] = []
        seen: set[str] = set()
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "fact.created":
                continue
            p = event.payload
            candidates = list(p.get("about_character_names", []))
            statuses = p.get("character_statuses")
            if isinstance(statuses, dict):
                candidates.extend(statuses.keys())
            for name in candidates:
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    # --------------------------------------------------------------- resolve

    def resolve(self, content: str) -> AliasResolutionResult:
        """Run the alias LLM pass and commit alias-bound events.

        Failure-isolated: any LLM error leaves the alias map untouched and the
        detector falls back to exact-name grouping.
        """
        result = AliasResolutionResult()
        if self.llm is None:
            result.llm_error = "no_llm_configured"
            return result

        names = self._fact_names()
        if len(names) < 2:
            # Nothing could co-refer; skip the call entirely.
            result.llm_succeeded = True
            return result

        try:
            groups = self._llm_resolve(content, names)
        except Exception as exc:  # noqa: BLE001 - isolate; never block writing
            logger.warning("alias resolution LLM stage failed: %s", exc)
            result.llm_error = str(exc)
            return result

        result.llm_succeeded = True
        result.groups = groups

        name_set = set(names)
        batch_id = self._new_id("alias")
        for group in groups:
            # Guard: only bind names the LLM was actually given (no invented
            # names), and never bind a name to itself as an alias.
            if group.canonical not in name_set:
                continue
            aliases = [
                a for a in group.aliases if a in name_set and a != group.canonical
            ]
            if not aliases:
                continue
            ce_id = self._new_id("alias")
            event_id = self._new_id("evt")
            self._writer.append(
                event_id=event_id,
                idempotency_key=f"{batch_id}:{ce_id}",
                event_type="character.alias_bound",
                payload={
                    "canonical_name": group.canonical,
                    "aliases": aliases,
                    "confidence": 0.8,
                    "source_batch_id": batch_id,
                },
                actor="extraction_agent",
                batch_id=batch_id,
            )
            result.bound_event_ids.append(ce_id)

        return result

    def _llm_resolve(self, content: str, names: list[str]) -> list[AliasGroup]:
        prompt = _ALIAS_TEMPLATE.format(
            names=", ".join(names),
            content=content,
        )
        response = self.llm.complete(prompt, system=_ALIAS_SYSTEM)
        data = self._parse_llm_json(response.text)

        groups: list[AliasGroup] = []
        for raw in data.get("groups", []):
            canonical = (raw.get("canonical") or "").strip()
            if not canonical:
                continue
            aliases = [
                (a or "").strip() for a in raw.get("aliases", []) if (a or "").strip()
            ]
            groups.append(AliasGroup(canonical=canonical, aliases=aliases))
        return groups

    @staticmethod
    def _parse_llm_json(text: str) -> dict:
        """Best-effort JSON extraction from an LLM response."""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            nl = text.find("\n")
            if nl != -1:
                text = text[nl + 1 :]
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise ValueError("LLM response contained no JSON object")
        return json.loads(text[first : last + 1])
