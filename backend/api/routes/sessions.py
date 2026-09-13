from uuid import UUID

from fastapi import APIRouter

from backend.api.dependencies import Service
from backend.models import (
    ActionRequest,
    HelpRequest,
    HelpResponse,
    SessionView,
    StartRequest,
)

router = APIRouter(prefix="/api/sessions")


@router.post("", response_model=SessionView, status_code=201)
def start(body: StartRequest, svc: Service):
    return svc.start(body.guide_id, body.platform)


@router.get("/{session_id}", response_model=SessionView)
def get_session(session_id: UUID, svc: Service):
    return svc.get(str(session_id))


@router.post("/{session_id}/actions", response_model=SessionView)
def act(session_id: UUID, body: ActionRequest, svc: Service):
    return svc.act(str(session_id), body)


@router.post("/{session_id}/help", response_model=HelpResponse)
def help_step(session_id: UUID, body: HelpRequest, svc: Service):
    return svc.help(str(session_id), body.question)
