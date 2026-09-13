from fastapi import APIRouter

from backend.api.dependencies import Service
from backend.models import Guide, Platform, SearchRequest, SearchResponse

router = APIRouter(prefix="/api")


@router.get("/guides", response_model=list[Guide])
def list_guides(svc: Service, platform: Platform = "ios"):
    return svc.knowledge.list(platform)


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, svc: Service):
    return svc.search(body.query, body.platform)
