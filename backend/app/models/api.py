"""API request and response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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
