"""Module API endpoints.

This implements the module-documents and optimistic-lock specs:
- GET/PUT module documents
- Lock management
- Classification endpoint
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.models.modules import MODULE_NAMES, ClassifyResponse, ModuleDocument
from app.services.classify import ClassifyService
from app.services.module_document import ModuleDocumentService
from app.services.project import ProjectService


router = APIRouter(prefix="/api/v1/projects/{project_id}/modules", tags=["modules"])


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from app.config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


# Request/Response models

class ModuleResponse(BaseModel):
    """Response for module document."""

    name: str
    content: str
    revision: int
    checksum: str
    sections: dict[str, str] = Field(default_factory=dict)


class UpdateModuleRequest(BaseModel):
    """Request to update a module document."""

    content: str
    revision: int = Field(..., description="Expected revision for optimistic locking")
    checksum: str = Field(..., description="Expected checksum for optimistic locking")


class UpdateModuleResponse(BaseModel):
    """Response after updating a module document."""

    name: str
    revision: int
    checksum: str
    message: str


class LockResponse(BaseModel):
    """Response for lock operations."""

    module: str
    locked: bool
    user_id: Optional[str] = None
    locked_at: Optional[datetime] = None
    ttl_seconds: Optional[int] = None
    message: str


class ClassifyRequest(BaseModel):
    """Request for content classification."""

    content: str
    world_summary: str = ""
    character_summary: str = ""
    plot_summary: str = ""


def get_module_service(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> ModuleDocumentService:
    """Get ModuleDocumentService for a project."""
    service = project_service.get_module_document_service(project_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return service


# Module document endpoints

@router.get("/{module_name}", response_model=ModuleResponse)
async def get_module(
    module_name: str,
    service: ModuleDocumentService = Depends(get_module_service),
) -> ModuleResponse:
    """Get a module document."""
    doc = service.get_module(module_name)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_name}' not found",
        )

    return ModuleResponse(
        name=doc.name,
        content=doc.raw_content,
        revision=doc.revision,
        checksum=doc.checksum,
        sections={name: s.content for name, s in doc.sections.items()},
    )


@router.put("/{module_name}", response_model=UpdateModuleResponse)
async def update_module(
    module_name: str,
    request: UpdateModuleRequest,
    service: ModuleDocumentService = Depends(get_module_service),
) -> UpdateModuleResponse:
    """Update a module document (user edit)."""
    if module_name not in MODULE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module name: {module_name}",
        )

    # Check for lock
    lock = service.get_lock(module_name)
    if lock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Module '{module_name}' is locked by user '{lock.user_id}'",
        )

    # Parse new content
    from app.services.module_parser import ModuleParser
    parser = ModuleParser()
    doc = parser.parse(module_name, request.content)
    doc.revision = request.revision

    # Save
    updated_doc = service.save_module(doc)

    return UpdateModuleResponse(
        name=updated_doc.name,
        revision=updated_doc.revision,
        checksum=updated_doc.checksum,
        message="Module updated successfully",
    )


# Lock endpoints

@router.post("/{module_name}/lock", response_model=LockResponse)
async def acquire_lock(
    module_name: str,
    user_id: str = "default_user",  # TODO: Get from auth
    service: ModuleDocumentService = Depends(get_module_service),
) -> LockResponse:
    """Acquire a lock on a module document."""
    if module_name not in MODULE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module name: {module_name}",
        )

    success, lock = service.acquire_lock(module_name, user_id)

    if not success and lock:
        # Lock conflict
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Module '{module_name}' is locked by user '{lock.user_id}'",
        )

    return LockResponse(
        module=module_name,
        locked=True,
        user_id=lock.user_id if lock else None,
        locked_at=lock.locked_at if lock else None,
        ttl_seconds=lock.ttl_seconds if lock else None,
        message="Lock acquired successfully",
    )


@router.delete("/{module_name}/lock", response_model=LockResponse)
async def release_lock(
    module_name: str,
    user_id: str = "default_user",  # TODO: Get from auth
    service: ModuleDocumentService = Depends(get_module_service),
) -> LockResponse:
    """Release a lock on a module document."""
    if module_name not in MODULE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module name: {module_name}",
        )

    success = service.release_lock(module_name, user_id)

    return LockResponse(
        module=module_name,
        locked=False,
        message="Lock released successfully" if success else "Lock not found or not owned by user",
    )


@router.post("/{module_name}/heartbeat", response_model=LockResponse)
async def extend_lock(
    module_name: str,
    user_id: str = "default_user",  # TODO: Get from auth
    service: ModuleDocumentService = Depends(get_module_service),
) -> LockResponse:
    """Extend a lock on a module document."""
    if module_name not in MODULE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module name: {module_name}",
        )

    success = service.extend_lock(module_name, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lock not found, expired, or not owned by user",
        )

    lock = service.get_lock(module_name)
    return LockResponse(
        module=module_name,
        locked=True,
        user_id=lock.user_id if lock else None,
        locked_at=lock.locked_at if lock else None,
        ttl_seconds=lock.ttl_seconds if lock else None,
        message="Lock extended successfully",
    )
