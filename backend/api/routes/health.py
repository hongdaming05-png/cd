from fastapi import APIRouter

from backend.api.dependencies import AppSettings, Service

router = APIRouter()


@router.get("/health")
def health(svc: Service, settings: AppSettings):
    return {
        "status": "ok",
        "guide_count": len(svc.knowledge.guides),
        "llm_provider": settings.llm_provider,
        "speech_provider": settings.speech_provider,
    }
