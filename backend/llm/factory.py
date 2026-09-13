"""Choose the configured explainer without exposing providers to callers."""

from backend.config import Settings
from backend.llm.base import Explainer
from backend.llm.client import HTTPExplainer


def create_explainer(settings: Settings) -> Explainer | None:
    if settings.llm_provider == "none":
        return None
    return HTTPExplainer(settings)
