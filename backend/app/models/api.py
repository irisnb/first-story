"""API request and response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .common import CharacterStatus
from .events import EventType


# Request models


class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")


class AppendEventRequest(BaseModel):
    """Request to append a new event."""

    event_id: str = Field(..., description="Globally unique event identity")
    idempotency_key: str = Field(..., description="Stable deduplication key")
    type: str = Field(..., description="Event type")
    schema_version: str = Field(default="1.0", description="Schema version")
    payload: dict[str, Any] = Field(..., description="Event payload")
    base_state_version: int = Field(
        default=0, ge=0, description="State version observed when proposing"
    )
    actor: str = Field(default="user", description="Origin of the event")
    batch_id: Optional[str] = Field(None, description="Batch identifier")

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event type is a known EventType."""
        try:
            EventType(v)
        except ValueError:
            valid_types = [e.value for e in EventType]
            raise ValueError(
                f"Unknown event type '{v}'. Valid types: {', '.join(valid_types)}"
            ) from None
        return v

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        """Validate payload based on event type."""
        event_type = info.data.get("type")
        if not event_type:
            return v

        if event_type == "character.created":
            # Validate character_id is present
            if "character_id" not in v:
                raise ValueError("payload must contain 'character_id' for character.created event")

            # Validate initial_status if present
            if "initial_status" in v:
                status = v["initial_status"]
                valid_statuses = [s.value for s in CharacterStatus]
                if status not in valid_statuses:
                    raise ValueError(
                        f"Invalid initial_status '{status}'. Valid values: {', '.join(valid_statuses)}"
                    )

        return v


# Response models


class ProjectResponse(BaseModel):
    """Response for a single project."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    version: str


class ProjectListResponse(BaseModel):
    """Response for listing projects."""

    projects: list[ProjectResponse]
    total: int


class EventResponse(BaseModel):
    """Response for a single event."""

    event_id: str
    idempotency_key: str
    seq: int
    timestamp: datetime
    type: str
    schema_version: str
    payload: dict[str, Any]
    base_state_version: int
    actor: str
    batch_id: Optional[str]


class EventListResponse(BaseModel):
    """Response for listing events."""

    events: list[EventResponse]
    total: int
    project_id: str


class StateResponse(BaseModel):
    """Response for story state."""

    projection_schema_version: str
    log_head_seq: int
    head_event_id: Optional[str]
    source_document_revision: Optional[str]
    source_document_checksum: Optional[str]
    story: dict[str, Any]
    updated_at: Optional[datetime]


class RebuildResponse(BaseModel):
    """Response for projection rebuild."""

    message: str
    log_head_seq: int
    events_processed: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    status: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
