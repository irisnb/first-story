"""API routes for the First Story backend."""

from fastapi import APIRouter

from .events import router as events_router
from .projects import router as projects_router
from .state import router as state_router

router = APIRouter()
router.include_router(projects_router, tags=["projects"])
router.include_router(events_router, tags=["events"])
router.include_router(state_router, tags=["state"])

__all__ = ["router"]
