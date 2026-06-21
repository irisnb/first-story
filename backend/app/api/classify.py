"""Classify API endpoint.

This implements the classify-api spec.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models.modules import ClassifyResponse
from app.services.classify import ClassifyService
from app.services.project import ProjectService


router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["classify"])


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from app.config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


class ClassifyRequest(BaseModel):
    """Request for content classification."""

    content: str = Field(..., description="User content to classify")
    world_summary: str = Field(default="", description="Current world summary")
    character_summary: str = Field(default="", description="Current character summary")
    plot_summary: str = Field(default="", description="Current plot summary")


@router.post("/classify", response_model=ClassifyResponse)
async def classify_content(
    project_id: str,
    request: ClassifyRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> ClassifyResponse:
    """Classify user content into modules and sections.

    This is an independent API for content classification.
    Called after each candidate message in dialogue flow.
    """
    # Get LLM provider from settings
    from app.config import get_settings
    from app.services.llm_provider import get_provider

    settings = get_settings()
    llm = None
    if settings.llm_api_key:
        llm = get_provider(settings)

    service = ClassifyService(llm_provider=llm)
    return await service.classify(
        content=request.content,
        world_summary=request.world_summary,
        character_summary=request.character_summary,
        plot_summary=request.plot_summary,
    )
