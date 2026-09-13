"""Small Ollama agent that turns speech or natural language into a RAG query."""

import json
import re

import httpx

from backend.config import Settings


class SearchAgent:
    def __init__(self, settings: Settings):
        self.settings = settings

    def rewrite(self, utterance: str) -> str:
        prompt = (
            "你是手機教學搜尋助手。把使用者口語改成最適合搜尋教學的繁體中文短語。"
            '只回傳 JSON：{"query":"..."}。不得回答問題、不得捏造功能。'
            f"使用者說：{utterance}"
        )
        body = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
        try:
            with httpx.Client(timeout=self.settings.llm_timeout) as client:
                response = client.post(
                    self.settings.llm_base_url.rstrip("/") + "/api/chat", json=body
                )
                response.raise_for_status()
            value = json.loads(response.json()["message"]["content"])["query"]
            return re.sub(r"\s+", " ", str(value)).strip()[:200] or utterance
        except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return utterance
