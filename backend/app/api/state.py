"""State API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import RebuildResponse, StateResponse
from ..services import ProjectService

router = APIRouter(prefix="/projects/{project_id}/state")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


@router.get("", response_model=StateResponse)
async def get_state(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> StateResponse:
    """Get the current story state projection."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    _, projector = services

    # Try to load cached state
    state = projector.load_state()
    if not state:
        # Rebuild if no cached state
        state = projector.rebuild()

    return StateResponse(**state.model_dump())


@router.post("/rebuild", response_model=RebuildResponse)
async def rebuild_state(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> RebuildResponse:
    """Force rebuild the story state from event log."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, projector = services

    state = projector.rebuild()

    return RebuildResponse(
        message="State rebuilt successfully",
        log_head_seq=state.log_head_seq,
        events_processed=event_log.get_event_count(),
    )
