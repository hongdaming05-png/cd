"""Provider-independent interface consumed by agents and services."""

from typing import Protocol

from backend.models import ModelAnswer, Passage


class Explainer(Protocol):
    def explain(self, question: str, passages: list[Passage]) -> ModelAnswer: ...
