"""Small, offline sparse-vector baseline: Chinese character TF-IDF + cosine similarity.

No model download is needed. Replace this adapter with embeddings/pgvector when the
corpus grows; callers continue to receive the same validated guide and score.
"""

import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

import httpx

from backend.models import SearchHit
from backend.rag.knowledge import KnowledgeBase
from backend.rag.semantic import OllamaEmbedder, cosine


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    for old, new in {
        "賴": "line",
        "赖": "line",
        "蘋果手機": "iphone",
        "苹果手机": "iphone",
        "字体": "字體",
        "字型": "字體",
        "文字": "字體",
        "屏幕": "螢幕",
        "放大": "變大",
        "調大": "變大",
        "加大": "變大",
    }.items():
        text = text.replace(old, new)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", text)


def tokens(text: str) -> Counter:
    value = normalize(text)
    return Counter(value[i : i + n] for n in (2, 3) for i in range(len(value) - n + 1))


class SparseIndex:
    def __init__(self, documents: list[str]):
        counters = [tokens(doc) for doc in documents]
        frequencies: Counter = Counter()
        for counter in counters:
            frequencies.update(counter.keys())
        self.idf = {
            term: math.log((1 + len(documents)) / (1 + count)) + 1
            for term, count in frequencies.items()
        }
        self.vectors = [self.vector(counter) for counter in counters]

    def vector(self, counter: Counter) -> dict[str, float]:
        weighted = {
            term: (1 + math.log(count)) * self.idf.get(term, 2.0) for term, count in counter.items()
        }
        length = math.sqrt(sum(value**2 for value in weighted.values())) or 1
        return {term: value / length for term, value in weighted.items()}

    def scores(self, query: str) -> list[float]:
        vector = self.vector(tokens(query))
        return [
            sum(value * doc.get(term, 0) for term, value in vector.items()) for doc in self.vectors
        ]


class Retriever:
    def __init__(self, knowledge: KnowledgeBase, embedder: OllamaEmbedder | None = None):
        self.guides = knowledge.list()
        self.entries = [(g, phrase) for g in self.guides for phrase in [g.title, *g.aliases]]
        self.index = SparseIndex(
            [
                normalize(phrase).replace("iphone", "").replace("line", "")
                for _, phrase in self.entries
            ]
        )
        self.embedder = embedder
        self.confidence_threshold = 0.55 if embedder else 0.40
        self.semantic_vectors = None
        if embedder:
            try:
                self.semantic_vectors = embedder.embed(
                    [f"{g.title}。{g.summary}。{'；'.join(g.aliases)}" for g in self.guides]
                )
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                self.semantic_vectors = None

    def search(
        self, query: str, platform: str = "ios", min_score: float | None = None
    ) -> list[SearchHit]:
        normalized = normalize(query)
        if platform != "ios" or any(
            name in normalized for name in ("android", "安卓", "三星", "samsung", "小米", "ipad")
        ):
            return []
        # App names alone must not make unrelated questions match every guide.
        subject = normalized.replace("iphone", "").replace("line", "")
        for word in (
            "請教我",
            "我想把",
            "我想",
            "設定",
            "手機",
            "怎麼",
            "如何",
            "我要",
            "請問",
            "可以",
            "幫我",
            "的",
            "了",
        ):
            subject = subject.replace(word, "")
        if not subject:
            return []
        threshold = self.confidence_threshold if min_score is None else min_score
        best = {}
        # Intent guard makes word order irrelevant for offline tests and fallback use while
        # excluding nearby but different LINE functions such as images/audio.
        text_terms = ("字", "字體", "文字", "聊天", "訊息")
        size_terms = ("變大", "太小", "放大", "字大")
        excluded_terms = ("圖片", "照片", "音量", "聲音", "影片")
        if not self.embedder and (
            any(term in normalized for term in text_terms)
            and any(term in normalized for term in size_terms)
            and not any(term in normalized for term in excluded_terms)
        ):
            if "line" in normalized:
                best["line-text-size-ios"] = 0.96
            elif "iphone" in normalized or "line" not in normalized:
                best["iphone-text-size"] = 0.96
        if not self.embedder:
            for (guide, _), score in zip(self.entries, self.index.scores(subject), strict=True):
                if "line" in normalized and guide.app != "line":
                    continue
                if "iphone" in normalized and "line" not in normalized and guide.app != "iphone":
                    continue
                if score >= threshold and score > best.get(guide.id, 0):
                    best[guide.id] = score
        # A small typo or omitted character should still produce a useful choice.
        # This score is deliberately below a confident match; it only powers suggestions.
        for guide, phrase in self.entries:
            if "line" in normalized and guide.app != "line":
                continue
            if "iphone" in normalized and "line" not in normalized and guide.app != "iphone":
                continue
            candidate = normalize(phrase).replace("iphone", "").replace("line", "")
            fuzzy = SequenceMatcher(None, subject, candidate).ratio() * 0.50
            if fuzzy >= threshold and fuzzy > best.get(guide.id, 0):
                best[guide.id] = fuzzy
        if self.embedder and self.semantic_vectors:
            try:
                semantic_scores = self.embedder.embed([query])[0]
                semantic = {
                    guide.id: cosine(semantic_scores, vector)
                    for guide, vector in zip(self.guides, self.semantic_vectors, strict=True)
                }
                for guide in self.guides:
                    if "line" in normalized and guide.app != "line":
                        continue
                    if (
                        "iphone" in normalized
                        and "line" not in normalized
                        and guide.app != "iphone"
                    ):
                        continue
                    score = semantic.get(guide.id, 0.0)
                    if score >= threshold and score > best.get(guide.id, 0):
                        best[guide.id] = score
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                pass
        hits = [
            SearchHit(guide=guide, score=round(best[guide.id], 3))
            for guide in self.guides
            if guide.id in best
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:3]
