"""HTTP adapter for Ollama and compatible chat APIs."""

import json

import httpx

from backend.config import Settings
from backend.llm.prompts import SYSTEM
from backend.models import ModelAnswer, Passage


class HTTPExplainer:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def explain(self, question: str, passages: list[Passage]) -> ModelAnswer:
        settings = self.settings
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "evidence": [passage.model_dump() for passage in passages],
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        body = {"model": settings.llm_model, "messages": messages, "stream": False}
        headers = {}
        if settings.llm_provider == "ollama":
            path = "/api/chat"
            body.update(format=ModelAnswer.model_json_schema(), options={"temperature": 0})
        else:
            path = "/chat/completions"
            body["response_format"] = {"type": "json_object"}
            key = settings.llm_api_key.get_secret_value()
            if key:
                headers["Authorization"] = f"Bearer {key}"
        with httpx.Client(timeout=settings.llm_timeout, transport=self.transport) as client:
            response = client.post(
                settings.llm_base_url.rstrip("/") + path, json=body, headers=headers
            )
            response.raise_for_status()
        data = response.json()
        if settings.llm_provider == "ollama":
            text = data["message"]["content"]
        else:
            text = data["choices"][0]["message"]["content"]
        answer = ModelAnswer.model_validate_json(text)
        if not set(answer.evidence_ids).issubset({passage.id for passage in passages}):
            raise ValueError("Model cited unknown evidence")
        return answer
