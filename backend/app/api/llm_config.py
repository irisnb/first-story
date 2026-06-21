"""LLM Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.llm_config import (
    LLMConfigListResponse,
    LLMConfigResponse,
    LLMConfigSlot,
    LLMConfigUpdateRequest,
)
from app.services.llm_config import LLMConfigService
from app.services.project import ProjectService


router = APIRouter(prefix="/projects/{project_id}/llm-config", tags=["llm-config"])


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from app.config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


def get_llm_config_service(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> LLMConfigService:
    """Get LLMConfigService for a project."""
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    project_dir = project_service.get_project_dir(project_id)
    return LLMConfigService(project_dir, project_id)


@router.get("", response_model=LLMConfigListResponse)
async def list_configs(
    service: LLMConfigService = Depends(get_llm_config_service),
) -> LLMConfigListResponse:
    """List all LLM configs."""
    return LLMConfigListResponse(configs=service.get_all_configs())


@router.get("/{slot}", response_model=LLMConfigResponse)
async def get_config(
    slot: LLMConfigSlot,
    service: LLMConfigService = Depends(get_llm_config_service),
) -> LLMConfigResponse:
    """Get LLM config for a specific slot."""
    return service.get_config_response(slot)


@router.put("/{slot}", response_model=LLMConfigResponse)
async def update_config(
    slot: LLMConfigSlot,
    update: LLMConfigUpdateRequest,
    service: LLMConfigService = Depends(get_llm_config_service),
) -> LLMConfigResponse:
    """Update LLM config for a slot."""
    service.update_config(slot, update)
    return service.get_config_response(slot)


@router.delete("/{slot}")
async def delete_config(
    slot: LLMConfigSlot,
    service: LLMConfigService = Depends(get_llm_config_service),
) -> dict:
    """Delete LLM config for a slot (revert to environment variables)."""
    service.delete_config(slot)
    return {"status": "ok", "message": f"Config for slot '{slot}' deleted"}
