"""Idea Cards API endpoints.

Creative idea cards with revision tracking.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.project import ProjectService


router = APIRouter(prefix="/projects/{project_id}/idea-cards", tags=["idea-cards"])


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from app.config import get_settings
    settings = get_settings()
    return ProjectService(settings.projects_root)


# Request/Response models

class IdeaCardSource(BaseModel):
    """Source of an idea card."""
    message_id: Optional[str] = None
    excerpt: str


class IdeaCard(BaseModel):
    """Idea card model."""
    id: str
    current_revision_id: str
    status: str = "active"  # active, shelved, archived
    created_at: str
    updated_at: str
    source: Optional[IdeaCardSource] = None
    summary: str = ""  # 摘要，用于列表显示
    created_from: str = "auto"  # "auto" | "manual"


class IdeaCardRevision(BaseModel):
    """Idea card revision model."""
    revision_id: str
    card_id: str
    content: str
    created_at: str


class CreateIdeaCardRequest(BaseModel):
    """Request to create an idea card."""
    content: str
    source: Optional[IdeaCardSource] = None
    summary: str = ""  # 摘要
    created_from: str = "manual"  # 手动创建默认为 "manual"


class UpdateIdeaCardRequest(BaseModel):
    """Request to update an idea card."""
    content: str


class UpdateStatusRequest(BaseModel):
    """Request to update card status."""
    status: str = Field(..., pattern="^(active|shelved|archived)$")


class IdeaCardResponse(BaseModel):
    """Response for a single idea card."""
    card: IdeaCard
    revision: IdeaCardRevision


class IdeaCardListResponse(BaseModel):
    """Response for listing idea cards."""
    cards: list[IdeaCard]
    revisions: list[IdeaCardRevision]


def _get_project_dir(project_service: ProjectService, project_id: str):
    """Get project directory, raise 404 if not found."""
    project_dir = project_service.projects_root / project_id
    if not project_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project_dir


def _load_cards(project_dir) -> tuple[list[dict], list[dict]]:
    """Load cards and revisions from files."""
    import json
    
    cards_file = project_dir / "idea_cards.json"
    revisions_file = project_dir / "idea_card_revisions.json"
    
    cards = []
    revisions = []
    
    if cards_file.exists():
        with open(cards_file, "r", encoding="utf-8") as f:
            cards = json.load(f)
    
    if revisions_file.exists():
        with open(revisions_file, "r", encoding="utf-8") as f:
            revisions = json.load(f)
    
    return cards, revisions


def _save_cards(project_dir, cards: list[dict], revisions: list[dict]):
    """Save cards and revisions to files."""
    import json
    
    cards_file = project_dir / "idea_cards.json"
    revisions_file = project_dir / "idea_card_revisions.json"
    
    with open(cards_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    
    with open(revisions_file, "w", encoding="utf-8") as f:
        json.dump(revisions, f, ensure_ascii=False, indent=2)


# API endpoints

@router.get("", response_model=IdeaCardListResponse)
async def list_idea_cards(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> IdeaCardListResponse:
    """List all idea cards for a project."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    return IdeaCardListResponse(
        cards=[IdeaCard(**c) for c in cards],
        revisions=[IdeaCardRevision(**r) for r in revisions],
    )


class CardExistsResponse(BaseModel):
    """Response for checking if a card exists for a message."""
    exists: bool


@router.get("/check/{message_id}", response_model=CardExistsResponse)
async def check_card_exists(
    project_id: str,
    message_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> CardExistsResponse:
    """Check if an idea card already exists for a given message ID.
    
    Used by frontend to show "already collected" state for chat messages.
    """
    project_dir = _get_project_dir(project_service, project_id)
    cards, _ = _load_cards(project_dir)
    
    exists = any(
        (card.get("source") or {}).get("message_id") == message_id
        for card in cards
    )
    
    return CardExistsResponse(exists=exists)


@router.post("", response_model=IdeaCardResponse, status_code=status.HTTP_201_CREATED)
async def create_idea_card(
    project_id: str,
    request: CreateIdeaCardRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> IdeaCardResponse:
    """Create a new idea card."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    now = datetime.now(timezone.utc).isoformat()
    card_id = f"card_{uuid4().hex[:8]}"
    revision_id = f"rev_{uuid4().hex[:8]}"
    
    # Create card
    card = {
        "id": card_id,
        "current_revision_id": revision_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "source": request.source.model_dump() if request.source else None,
        "summary": request.summary or "",
        "created_from": request.created_from or "manual",
    }
    
    # Create revision
    revision = {
        "revision_id": revision_id,
        "card_id": card_id,
        "content": request.content,
        "created_at": now,
    }
    
    cards.append(card)
    revisions.append(revision)
    _save_cards(project_dir, cards, revisions)
    
    return IdeaCardResponse(
        card=IdeaCard(**card),
        revision=IdeaCardRevision(**revision),
    )


@router.get("/{card_id}", response_model=IdeaCardResponse)
async def get_idea_card(
    project_id: str,
    card_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> IdeaCardResponse:
    """Get a specific idea card."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    card = next((c for c in cards if c["id"] == card_id), None)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card '{card_id}' not found",
        )
    
    revision = next(
        (r for r in revisions if r["revision_id"] == card["current_revision_id"]),
        None,
    )
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Card revision not found",
        )
    
    return IdeaCardResponse(
        card=IdeaCard(**card),
        revision=IdeaCardRevision(**revision),
    )


@router.put("/{card_id}", response_model=IdeaCardResponse)
async def update_idea_card(
    project_id: str,
    card_id: str,
    request: UpdateIdeaCardRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> IdeaCardResponse:
    """Update an idea card (creates new revision)."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    card_idx = next((i for i, c in enumerate(cards) if c["id"] == card_id), None)
    if card_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card '{card_id}' not found",
        )
    
    now = datetime.now(timezone.utc).isoformat()
    revision_id = f"rev_{uuid4().hex[:8]}"
    
    # Create new revision
    revision = {
        "revision_id": revision_id,
        "card_id": card_id,
        "content": request.content,
        "created_at": now,
    }
    revisions.append(revision)
    
    # Update card
    cards[card_idx]["current_revision_id"] = revision_id
    cards[card_idx]["updated_at"] = now
    
    _save_cards(project_dir, cards, revisions)
    
    return IdeaCardResponse(
        card=IdeaCard(**cards[card_idx]),
        revision=IdeaCardRevision(**revision),
    )


@router.patch("/{card_id}/status", response_model=IdeaCard)
async def update_card_status(
    project_id: str,
    card_id: str,
    request: UpdateStatusRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> IdeaCard:
    """Update card status (active/shelved/archived)."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    card_idx = next((i for i, c in enumerate(cards) if c["id"] == card_id), None)
    if card_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card '{card_id}' not found",
        )
    
    cards[card_idx]["status"] = request.status
    cards[card_idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    _save_cards(project_dir, cards, revisions)
    
    return IdeaCard(**cards[card_idx])


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_idea_card(
    project_id: str,
    card_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> None:
    """Delete an idea card (soft delete - marks as archived)."""
    project_dir = _get_project_dir(project_service, project_id)
    cards, revisions = _load_cards(project_dir)
    
    card_idx = next((i for i, c in enumerate(cards) if c["id"] == card_id), None)
    if card_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card '{card_id}' not found",
        )
    
    # Soft delete: mark as archived instead of removing
    cards[card_idx]["status"] = "archived"
    cards[card_idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    _save_cards(project_dir, cards, revisions)
