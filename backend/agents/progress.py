"""User-confirmed progress graph; never calls a model."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.models import Session


class ProgressState(TypedDict):
    session: Session
    action: str


def build_progress_graph():
    def advance(state: ProgressState):
        session = state["session"].model_copy(deep=True)
        if session.status == "completed":
            raise ValueError("教學已完成，可選擇重新練習。")
        if session.step_index == len(session.guide.steps) - 1:
            session.status = "completed"
        else:
            session.step_index += 1
        return {"session": session}

    def back(state: ProgressState):
        session = state["session"].model_copy(deep=True)
        if session.status == "completed":
            session.status = "active"
        else:
            session.step_index = max(0, session.step_index - 1)
        return {"session": session}

    def restart(state: ProgressState):
        return {
            "session": state["session"].model_copy(update={"step_index": 0, "status": "active"})
        }

    graph = StateGraph(ProgressState)
    for name, node in (("next", advance), ("back", back), ("restart", restart)):
        graph.add_node(name, node)
        graph.add_edge(name, END)
    graph.add_conditional_edges(
        START, lambda state: state["action"], {name: name for name in ("next", "back", "restart")}
    )
    return graph.compile()
