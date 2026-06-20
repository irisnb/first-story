"""Documents API endpoints - save / list / restore manuscript revisions."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..models.documents import DocumentRevision
from ..services import ProjectService, to_fountain, to_plain_text

router = APIRouter(prefix="/projects/{project_id}/documents")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings

    settings = get_settings()
    return ProjectService(settings.projects_root)


class SaveRevisionRequest(BaseModel):
    """Request to save a new manuscript revision."""

    content: str = Field(..., description="Full manuscript prose to save")
    document_id: str = Field(default="main", description="Document identifier")


class RevisionListResponse(BaseModel):
    """A list of manuscript revisions."""

    revisions: list[DocumentRevision]
    total: int
    project_id: str


def _resolve(project_service: ProjectService, project_id: str):
    doc_service = project_service.get_document_service(project_id)
    if not doc_service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return doc_service


def _run_extraction_batch(
    project_service: ProjectService,
    project_id: str,
    content: str,
    revision: str,
) -> None:
    """Background batch extraction triggered after an editor save.

    Delegates to the shared extraction pipeline in committed/document mode.
    Any failure is isolated inside the pipeline so it never propagates back to
    the user's save request.
    """
    from ..services.extraction_pipeline import run_extraction_pipeline

    run_extraction_pipeline(
        project_service,
        project_id,
        content=content,
        source_type="document",
        source_id=revision,
        acceptance_status="committed",
    )


@router.post("", response_model=DocumentRevision, status_code=status.HTTP_201_CREATED)
async def save_revision(
    project_id: str,
    request: SaveRevisionRequest,
    background_tasks: BackgroundTasks,
    project_service: ProjectService = Depends(get_project_service),
) -> DocumentRevision:
    """Save the manuscript as a new revision (append-only, never overwrites).

    Extraction is queued as a background batch after the save returns - it is
    never run per-keystroke and never blocks the save itself.
    """
    doc_service = _resolve(project_service, project_id)
    revision = doc_service.save_revision(
        request.content, document_id=request.document_id
    )
    # Keep the state projection in sync immediately (document text projection).
    _, projector = project_service.get_services(project_id)
    projector.rebuild()
    project_service._update_project_timestamp(project_id)
    # Queue extraction as a post-save batch (does not block the response).
    background_tasks.add_task(
        _run_extraction_batch,
        project_service,
        project_id,
        request.content,
        revision.revision_id,
    )
    return revision


@router.get("/export", response_class=PlainTextResponse)
async def export_document(
    project_id: str,
    document_id: str = "main",
    format: str = "fountain",
    project_service: ProjectService = Depends(get_project_service),
) -> PlainTextResponse:
    """Export the current manuscript as Fountain or plain text.

    format='fountain' keeps Fountain structure; format='text' strips markers.
    """
    doc_service = _resolve(project_service, project_id)
    revisions = doc_service.list_revisions(document_id=document_id)
    content = revisions[-1].content if revisions else ""

    if format == "text":
        rendered = to_plain_text(content)
        media_type = "text/plain; charset=utf-8"
        filename = f"{document_id}.txt"
    elif format == "fountain":
        rendered = to_fountain(content)
        media_type = "text/plain; charset=utf-8"
        filename = f"{document_id}.fountain"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}' (use 'fountain' or 'text')",
        )

    return PlainTextResponse(
        content=rendered,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("", response_model=RevisionListResponse)
async def list_revisions(
    project_id: str,
    document_id: str = "main",
    project_service: ProjectService = Depends(get_project_service),
) -> RevisionListResponse:
    """List all historical revisions of a document, oldest first."""
    doc_service = _resolve(project_service, project_id)
    revisions = doc_service.list_revisions(document_id=document_id)
    return RevisionListResponse(
        revisions=revisions, total=len(revisions), project_id=project_id
    )


@router.post("/{revision_id}/restore", response_model=DocumentRevision)
async def restore_revision(
    project_id: str,
    revision_id: str,
    document_id: str = "main",
    project_service: ProjectService = Depends(get_project_service),
) -> DocumentRevision:
    """Restore an old revision by appending it as a new revision."""
    doc_service = _resolve(project_service, project_id)
    revision = doc_service.restore_revision(revision_id, document_id=document_id)
    if revision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revision '{revision_id}' not found",
        )
    _, projector = project_service.get_services(project_id)
    projector.rebuild()
    project_service._update_project_timestamp(project_id)
    return revision
