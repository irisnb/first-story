"""Projects API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
)
from ..services import ProjectService

router = APIRouter(prefix="/projects")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """List all projects."""
    projects = project_service.list_projects()
    return ProjectListResponse(
        projects=[ProjectResponse(**p.model_dump()) for p in projects],
        total=len(projects),
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Create a new project."""
    project = project_service.create_project(request.name)
    return ProjectResponse(**project.model_dump())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Get a project by ID."""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return ProjectResponse(**project.model_dump())
