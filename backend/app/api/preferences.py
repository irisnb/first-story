"""Preferences / evidence-card API - user ignore/accept of continuity findings."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services import ProjectService

router = APIRouter(prefix="/projects/{project_id}/continuity-events")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings

    settings = get_settings()
    return ProjectService(settings.projects_root)


class IgnoreRequest(BaseModel):
    """Request to ignore a continuity evidence card."""

    user_explanation: str | None = Field(
        None, description="Optional reason the user is ignoring this finding"
    )
    scope: str = Field(
        default="single_finding",
        description="'single_finding' or 'category' (category writes a de-weighting rule)",
    )


class AcceptRequest(BaseModel):
    """Request to accept a continuity evidence card."""

    resolution_fact_id: str | None = Field(
        None, description="Optional fact id that resolves the conflict"
    )


class CardActionResponse(BaseModel):
    """Result of an ignore/accept action."""

    continuity_event_id: str
    action: str
    deweighting_written: bool = False
    category: str | None = None


def _resolve(project_service: ProjectService, project_id: str):
    svc = project_service.get_evidence_card_service(project_id)
    if not svc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return svc


@router.post("/{continuity_event_id}/ignore", response_model=CardActionResponse)
async def ignore_card(
    project_id: str,
    continuity_event_id: str,
    request: IgnoreRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> CardActionResponse:
    """Ignore an evidence card. Judgment stays with the user.

    With scope='category', a de-weighting rule is recorded - the detection is
    NOT disabled, future same-category findings are merely lower priority.
    """
    svc = _resolve(project_service, project_id)
    result = svc.ignore(
        continuity_event_id,
        user_explanation=request.user_explanation,
        scope=request.scope,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Continuity event '{continuity_event_id}' not found",
        )
    # Keep the projection in sync (status -> ignored, preference recorded).
    _, projector = project_service.get_services(project_id)
    projector.rebuild()
    return CardActionResponse(
        continuity_event_id=result.continuity_event_id,
        action=result.action,
        deweighting_written=result.deweighting_written,
        category=result.category,
    )


@router.post("/{continuity_event_id}/accept", response_model=CardActionResponse)
async def accept_card(
    project_id: str,
    continuity_event_id: str,
    request: AcceptRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> CardActionResponse:
    """Accept an evidence card - mark confirmed/resolved, keep the record."""
    svc = _resolve(project_service, project_id)
    result = svc.accept(
        continuity_event_id, resolution_fact_id=request.resolution_fact_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Continuity event '{continuity_event_id}' not found",
        )
    _, projector = project_service.get_services(project_id)
    projector.rebuild()
    return CardActionResponse(
        continuity_event_id=result.continuity_event_id, action=result.action
    )
