"""Resolve application-scoped dependencies for HTTP endpoints."""

from typing import Annotated

from fastapi import Depends, Request

from backend.config import Settings
from backend.services import GuideService


def get_service(request: Request) -> GuideService:
    return request.app.state.service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


Service = Annotated[GuideService, Depends(get_service)]
AppSettings = Annotated[Settings, Depends(get_settings)]
