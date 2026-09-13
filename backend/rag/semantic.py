"""Small Ollama embedding adapter used as an optional semantic retrieval layer."""

import math

import httpx


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str = "bge-m3", timeout: float = 20):
        self.url = base_url.rstrip("/") + "/api/embed"
        self.model = model
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.url, json={"model": self.model, "input": texts})
            response.raise_for_status()
            values = response.json().get("embeddings")
        if not isinstance(values, list) or len(values) != len(texts):
            raise ValueError("Ollama embedding response is invalid")
        return values


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return dot / norm if norm else 0.0
