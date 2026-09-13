"""Single registration point for API route modules."""

from fastapi import APIRouter

from backend.api.routes import guides, health, sessions, speech

router = APIRouter()
router.include_router(health.router)
router.include_router(guides.router)
router.include_router(sessions.router)
router.include_router(speech.router)
