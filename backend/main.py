"""ASGI entry point: python -m uvicorn backend.main:app."""

from backend.application import create_app

app = create_app()
