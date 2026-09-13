from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.llm.search_agent import SearchAgent


class SearchState(TypedDict, total=False):
    utterance: str
    query: str


def build_search_graph(agent: SearchAgent | None):
    # LangGraph 在這裡刻意保持很小：Agent 只整理問法，不產生教學步驟。
    def interpret(state: SearchState) -> SearchState:
        utterance = state.get("utterance", "").strip()
        return {"query": agent.rewrite(utterance) if agent else utterance}

    graph = StateGraph(SearchState)
    graph.add_node("interpret_request", interpret)
    graph.add_edge(START, "interpret_request")
    graph.add_edge("interpret_request", END)
    return graph.compile()
