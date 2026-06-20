"""API routes for the First Story backend."""

from fastapi import APIRouter

from .documents import router as documents_router
from .events import router as events_router
from .preferences import router as preferences_router
from .projects import router as projects_router
from .state import router as state_router
from .chat import router as chat_router

router = APIRouter()
router.include_router(projects_router, tags=["projects"])
router.include_router(events_router, tags=["events"])
router.include_router(documents_router, tags=["documents"])
router.include_router(preferences_router, tags=["preferences"])
router.include_router(state_router, tags=["state"])
router.include_router(chat_router, tags=["chat"])

__all__ = ["router"]
