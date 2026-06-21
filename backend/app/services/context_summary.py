"""Context Summary Service - generates and updates dialogue context summaries.

Implements the layered summary mechanism:
- Minor summary (every 10 turns): updates recent_focus only
- Major summary (every 30 turns): updates all fields (world, plot, character, recent_focus)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ..models.state import ContextSummary
from .hub import get_hub

if TYPE_CHECKING:
    from .event_log import EventLogService
    from .llm_provider import LLMProvider
    from .projector import ProjectorService

logger = logging.getLogger("first_story.context_summary")

# Prompt templates
_MINOR_SUMMARY_PROMPT = """你是创作助手。请根据最近 10 轮对话，提炼用户最近在创作什么。

## 最近 10 轮对话
{chat_history}

请输出 JSON：
{{
  "recent_focus": "最近创作焦点（100字以内，用户最近在讨论/创作什么）"
}}

注意：
- 只关注最近的话题，不要回顾更早的内容
- 简洁，抓住核心
- 如果无法判断，写"暂无明确焦点"
"""

_MAJOR_SUMMARY_PROMPT = """你是创作助手。请根据以下信息生成项目摘要。

## 最近 30 轮对话
{chat_history}

## 当前故事状态
{story_state}

请输出 JSON：
{{
  "world_brief": "世界观简述（200字以内，包含核心设定、规则、风格）",
  "plot_brief": "情节简述（200字以内，包含主线进展、关键事件）",
  "character_brief": "角色简述（200字以内，主要角色的关键信息）",
  "recent_focus": "最近创作焦点（100字以内，用户最近在讨论什么）"
}}

注意：
- 简洁、抓重点，不要流水账
- 突出用户明确表达的内容，不要臆测
- 如果某方面信息不足，写"暂无"
"""


class ContextSummaryService:
    """Service for generating and updating context summaries."""

    def __init__(
        self,
        event_log: "EventLogService",
        projector: "ProjectorService",
        llm_provider: "LLMProvider | None" = None,
    ):
        self.event_log = event_log
        self.projector = projector
        self.llm = llm_provider

    def generate_minor_summary(self, recent_messages: list[str]) -> str:
        """Generate a minor summary (recent_focus only) from recent 10 turns.

        Args:
            recent_messages: List of message contents from recent turns

        Returns:
            The generated recent_focus string
        """
        if not self.llm:
            logger.warning("No LLM configured, skipping minor summary generation")
            return ""

        chat_history = "\n".join(f"- {msg}" for msg in recent_messages[-20:])  # 10 turns = 20 messages
        prompt = _MINOR_SUMMARY_PROMPT.format(chat_history=chat_history)

        try:
            response = self.llm.complete(prompt)
            data = self._parse_json_response(response.text)
            return data.get("recent_focus", "")
        except Exception as e:
            logger.error("Failed to generate minor summary: %s", e)
            return ""

    def generate_major_summary(
        self,
        recent_messages: list[str],
        story_state_summary: str,
    ) -> dict[str, str]:
        """Generate a major summary (all fields) from recent 30 turns.

        Args:
            recent_messages: List of message contents from recent turns
            story_state_summary: Summary of current story state

        Returns:
            Dict with world_brief, plot_brief, character_brief, recent_focus
        """
        if not self.llm:
            logger.warning("No LLM configured, skipping major summary generation")
            return {
                "world_brief": "",
                "plot_brief": "",
                "character_brief": "",
                "recent_focus": "",
            }

        chat_history = "\n".join(f"- {msg}" for msg in recent_messages[-60:])  # 30 turns = 60 messages
        prompt = _MAJOR_SUMMARY_PROMPT.format(
            chat_history=chat_history,
            story_state=story_state_summary,
        )

        try:
            response = self.llm.complete(prompt)
            data = self._parse_json_response(response.text)
            return {
                "world_brief": data.get("world_brief", ""),
                "plot_brief": data.get("plot_brief", ""),
                "character_brief": data.get("character_brief", ""),
                "recent_focus": data.get("recent_focus", ""),
            }
        except Exception as e:
            logger.error("Failed to generate major summary: %s", e)
            return {
                "world_brief": "",
                "plot_brief": "",
                "character_brief": "",
                "recent_focus": "",
            }

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Parse JSON from LLM response, handling code fences."""
        import json

        text = text.strip()
        # Strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            nl = text.find("\n")
            if nl != -1:
                text = text[nl + 1 :]

        # Find JSON object
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            return {}

        return json.loads(text[first : last + 1])

    def _get_recent_chat_messages(self, limit: int = 60) -> list[str]:
        """Get recent chat messages for summary generation.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message contents (user and assistant)
        """
        messages: list[str] = []
        for event in self.event_log.read_events():
            etype = event.type.value if hasattr(event.type, "value") else event.type
            if etype != "chat.message":
                continue
            content = event.payload.get("content", "")
            if content:
                messages.append(content)
        return messages[-limit:]

    def _write_summary_event(
        self,
        summary_type: str,
        turn_count: int,
        summary_data: dict[str, str],
    ) -> None:
        """Write a context_summary.updated event.

        Args:
            summary_type: "minor" or "major"
            turn_count: Current turn count
            summary_data: Dict with summary fields (world_brief, plot_brief, etc.)
        """
        writer = get_hub().writer_for(self.event_log)
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        payload = {
            "turn_count": turn_count,
            "summary_type": summary_type,
            **summary_data,
        }

        # Add timestamp based on summary type
        if summary_type == "minor":
            payload["last_minor_update"] = now
        else:
            payload["last_major_update"] = now

        writer.append(
            event_id=event_id,
            idempotency_key=f"context_summary:{event_id}",
            event_type="context_summary.updated",
            payload=payload,
            actor="hub",
        )

    def update_and_persist(
        self,
        summary_type: str,
        current_turn_count: int,
        story_state_summary: str = "",
    ) -> None:
        """Generate summary, write event, and rebuild projection.

        This is the main entry point for background summary updates.
        Failure-isolated: errors are logged but not raised.

        Args:
            summary_type: "minor" (update recent_focus) or "major" (update all fields)
            current_turn_count: Current turn count to record in the event
            story_state_summary: Summary of current story state (for major summaries)
        """
        try:
            if summary_type == "minor":
                recent_messages = self._get_recent_chat_messages(limit=20)
                recent_focus = self.generate_minor_summary(recent_messages)
                summary_data = {"recent_focus": recent_focus}
            else:  # major
                recent_messages = self._get_recent_chat_messages(limit=60)
                summary_data = self.generate_major_summary(recent_messages, story_state_summary)

            # Write the event
            self._write_summary_event(summary_type, current_turn_count, summary_data)

            # Rebuild projection
            self.projector.rebuild()

            logger.info(
                "Context summary updated: type=%s, turn_count=%d",
                summary_type,
                current_turn_count,
            )
        except Exception as e:
            logger.error("Failed to update context summary: %s", e)
            # Failure-isolated: don't raise, just log
