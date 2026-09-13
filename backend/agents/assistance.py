"""Retrieve evidence, explain, or fall back to curated guidance."""

import logging
from typing import TypedDict

import httpx
from langgraph.graph import END, START, StateGraph

from backend.llm.base import Explainer
from backend.models import HelpResponse, Passage, Session
from backend.rag.retrieval import SparseIndex

logger = logging.getLogger(__name__)


class HelpState(TypedDict, total=False):
    session: Session
    question: str
    passages: list[Passage]
    result: HelpResponse


def build_help_graph(explainer: Explainer | None = None):
    def retrieve(state: HelpState):
        session = state["session"]
        step = session.guide.steps[session.step_index]
        direct_help = any(
            word in state["question"]
            for word in ("找不到", "不一樣", "不會", "卡住", "這一步", "看不懂", "幫幫我")
        )
        if direct_help:
            passages = [
                Passage(id="current-instruction", text=step.instruction),
                Passage(id="current-hint", text=step.hint),
                Passage(id="current-check", text=step.checkpoint),
            ]
        else:
            faqs = session.guide.faqs
            scores = SparseIndex([faq.question for faq in faqs]).scores(state["question"])
            matches = sorted(zip(scores, faqs, strict=True), key=lambda item: item[0], reverse=True)
            passages = (
                [Passage(id="guide-faq", text=matches[0][1].answer)]
                if (matches and matches[0][0] >= 0.30)
                else []
            )
        return {"passages": passages}

    def reference(state: HelpState):
        passages = state["passages"]
        answer = "\n".join(passage.text for passage in passages)
        return {
            "result": HelpResponse(
                answer=answer,
                mode="reference",
                passages=passages,
                sources=state["session"].guide.sources,
            )
        }

    def unsupported(state: HelpState):
        return {
            "result": HelpResponse(
                answer="目前這份教學沒有足夠資訊回答這個問題。可以按「這一步找不到」看提示，"
                "或先請身邊的人一起確認畫面。",
                mode="unsupported",
                passages=[],
                sources=[],
            )
        }

    def generate(state: HelpState):
        try:
            answer = explainer.explain(state["question"], state["passages"])
            result = HelpResponse(
                answer=answer.answer,
                mode="ai",
                passages=state["passages"],
                sources=state["session"].guide.sources,
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            # Do not log provider bodies, user questions, prompts, or secrets.
            logger.warning("Model unavailable or invalid response; using reviewed content")
            result = reference(state)["result"].model_copy(update={"mode": "fallback"})
        return {"result": result}

    graph = StateGraph(HelpState)
    for name, node in (
        ("retrieve", retrieve),
        ("reference", reference),
        ("unsupported", unsupported),
        ("generate", generate),
    ):
        graph.add_node(name, node)
    graph.add_edge(START, "retrieve")

    def route(state):
        if not state["passages"]:
            return "unsupported"
        return "generate" if explainer is not None else "reference"

    graph.add_conditional_edges("retrieve", route)
    for name in ("reference", "unsupported", "generate"):
        graph.add_edge(name, END)
    return graph.compile()
