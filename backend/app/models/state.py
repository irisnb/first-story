"""StoryState and Story projection models.

This aligns with the minimal-story-state spec.
"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field

from .characters import Character
from .continuity import ContinuityEvent
from .documents import DocumentRevision
from .facts import Fact
from .modules import ModuleDocument
from .plot_events import PlotEvent
from .preferences import ConfirmedAssumptionPreference, DeweightingPreference


class StoryClock(BaseModel):
    """Structured story timeline state."""

    current_time: Optional[str] = Field(
        None, description="Current time in the story"
    )
    reference_point: str = Field(
        default="story_start", description="Reference point for time calculations"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence of the time state"
    )


class StyleMemo(BaseModel):
    """A global creative-direction note (e.g. "动画+collage 拼贴感").

    Style memos sit ALONGSIDE the five story modules - they are creative
    direction, NOT continuity facts, so they never enter contradiction
    detection. They are archived (status="archived"), never deleted.

    V1 structure: ``text`` (free-form, required) + optional ``kind`` (a coarse
    tag like form/tone, falling back to "未分类").
    """

    id: str = Field(..., description="Stable identifier")
    text: str = Field(..., description="Free-form creative direction note")
    kind: str = Field(default="未分类", description="Coarse tag (form/tone/...)")
    status: str = Field(
        default="active", description='"active" or "archived" - never deleted'
    )
    source_event_id: Optional[str] = Field(
        None, description="event_id that introduced this memo"
    )


class ContextSummary(BaseModel):
    """对话上下文摘要，用于帮助 LLM 快速进入状态。

    分层更新机制：
    - 小摘要（10轮）：只更新 recent_focus
    - 大摘要（30轮）：全面更新所有字段
    """

    # 大摘要（30轮更新）
    world_brief: str = Field(
        default="", description="世界观简述，200字以内"
    )
    plot_brief: str = Field(
        default="", description="情节简述，200字以内"
    )
    character_brief: str = Field(
        default="", description="角色简述，200字以内"
    )

    # 小摘要（10轮更新）
    recent_focus: str = Field(
        default="", description="最近创作焦点，100字以内"
    )

    # 元信息
    last_minor_update: Optional[str] = Field(
        None, description="小摘要更新时间"
    )
    last_major_update: Optional[str] = Field(
        None, description="大摘要更新时间"
    )
    turn_count: int = Field(
        default=0, description="当前对话轮数"
    )


class Story(BaseModel):
    """The story state content."""

    story_clock: Optional[StoryClock] = Field(
        None, description="Structured story timeline state"
    )
    characters: list[Character] = Field(
        default_factory=list, description="Character objects"
    )
    plot_events: list[PlotEvent] = Field(
        default_factory=list, description="PlotEvent objects"
    )
    facts: list[Fact] = Field(
        default_factory=list, description="Fact objects"
    )
    continuity_events: list[ContinuityEvent] = Field(
        default_factory=list, description="ContinuityEvent objects"
    )
    project_preferences: list[Union[ConfirmedAssumptionPreference, DeweightingPreference]] = Field(
        default_factory=list,
        description="Project-level preferences, deweighting rules, and confirmed assumptions",
    )
    current_document: Optional[DocumentRevision] = Field(
        None, description="Latest manuscript revision (projection of document.revised events)"
    )
    style_memos: list[StyleMemo] = Field(
        default_factory=list,
        description="Global creative-direction notes, level with the five modules. "
        "Never enter contradiction detection; archived, never deleted.",
    )
    context_summary: ContextSummary = Field(
        default_factory=ContextSummary,
        description="对话上下文摘要，帮助 LLM 快速进入状态",
    )
    modules: dict[str, ModuleDocument] = Field(
        default_factory=dict,
        description="Five module documents (world, characters, plot, theme, structure)",
    )


class StoryState(BaseModel):
    """The current story state projection.

    This is a rebuildable projection from the event log, NOT the source of truth.
    The event log is the source of truth for AI-structured story state.
    """

    projection_schema_version: str = Field(
        default="1.0", description="Schema version for projection structure"
    )
    log_head_seq: int = Field(
        default=0, description="Highest seq processed from event log"
    )
    head_event_id: Optional[str] = Field(
        None, description="event_id of the highest seq event"
    )
    source_document_revision: Optional[str] = Field(
        None, description="Document revision if tracked"
    )
    source_document_checksum: Optional[str] = Field(
        None, description="Document checksum if tracked"
    )
    story: Story = Field(
        default_factory=Story, description="The story state content"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When this projection was last updated"
    )
