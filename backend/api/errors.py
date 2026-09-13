"""Translate application errors into the existing HTTP response contract."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.repositories import ConflictError


async def not_found(request: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": "找不到這份教學或進度。"})


async def conflict(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def invalid_action(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(KeyError, not_found)
    app.add_exception_handler(ConflictError, conflict)
    app.add_exception_handler(ValueError, invalid_action)
