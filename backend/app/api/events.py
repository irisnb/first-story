"""Events API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import (
    AppendEventRequest,
    EventListResponse,
    EventResponse,
    SystemEvent,
)
from ..services import EventLogService, ProjectService

router = APIRouter(prefix="/projects/{project_id}/events")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


@router.get("", response_model=EventListResponse)
async def list_events(
    project_id: str,
    from_seq: int | None = None,
    to_seq: int | None = None,
    project_service: ProjectService = Depends(get_project_service),
) -> EventListResponse:
    """List events for a project."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, _ = services

    events = list(event_log.read_events(from_seq=from_seq, to_seq=to_seq))
    return EventListResponse(
        events=[EventResponse(**e.model_dump()) for e in events],
        total=len(events),
        project_id=project_id,
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def append_event(
    project_id: str,
    request: AppendEventRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> EventResponse:
    """Append a new event to the project."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, _ = services

    seq, was_new = event_log.append_event(
        event_id=request.event_id,
        idempotency_key=request.idempotency_key,
        event_type=request.type,
        payload=request.payload,
        base_state_version=request.base_state_version,
        actor=request.actor,
        batch_id=request.batch_id,
        schema_version=request.schema_version,
    )

    # Update project timestamp
    project_service._update_project_timestamp(project_id)

    # If duplicate, return existing event
    if not was_new:
        # Find and return the existing event
        for event in event_log.read_events(from_seq=seq, to_seq=seq):
            return EventResponse(**event.model_dump())

    # Return the new event
    return EventResponse(
        event_id=request.event_id,
        idempotency_key=request.idempotency_key,
        seq=seq,
        type=request.type,
        schema_version=request.schema_version,
        payload=request.payload,
        base_state_version=request.base_state_version,
        actor=request.actor,
        batch_id=request.batch_id,
        timestamp=event_log.read_events(from_seq=seq, to_seq=seq).__next__().timestamp if was_new else None,
    )
