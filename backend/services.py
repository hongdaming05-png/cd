from uuid import uuid4

from backend.agents.assistance import build_help_graph
from backend.agents.progress import build_progress_graph
from backend.agents.search import build_search_graph
from backend.llm.base import Explainer
from backend.llm.search_agent import SearchAgent
from backend.models import ActionRequest, HelpResponse, SearchResponse, Session, SessionView
from backend.rag.knowledge import KnowledgeBase
from backend.rag.retrieval import Retriever
from backend.rag.semantic import OllamaEmbedder
from backend.repositories import ConflictError, SessionStore
from backend.web import WebSearcher


class GuideService:
    def __init__(
        self,
        knowledge: KnowledgeBase,
        store: SessionStore,
        explainer: Explainer | None = None,
        search_agent: SearchAgent | None = None,
        web_searcher: WebSearcher | None = None,
        embedder: OllamaEmbedder | None = None,
    ):
        self.knowledge = knowledge
        self.store = store
        self.retriever = Retriever(knowledge, embedder)
        self.progress_graph = build_progress_graph()
        self.help_graph = build_help_graph(explainer)
        self.search_graph = build_search_graph(search_agent)
        self.web_searcher = web_searcher

    def search(self, query: str, platform: str) -> SearchResponse:
        # 搜尋固定走同一條管線：口語整理 → 本地 RAG → 沒命中才查公開網路。
        normalized = self.search_graph.invoke({"utterance": query})["query"]
        ranked = self.retriever.search(normalized, platform, min_score=0.28)
        hits = [hit for hit in ranked if hit.score >= self.retriever.confidence_threshold]
        suggestions = [hit for hit in ranked if hit.score < self.retriever.confidence_threshold]
        # 模糊的字體問題先顯示 LINE，再讓使用者選 iPhone 系統設定。
        suggestions.sort(key=lambda hit: (hit.score, hit.guide.app == "line"), reverse=True)
        suggestions = suggestions[:3] if not hits else []
        # 已有相近的本地教學時先讓使用者確認，避免多一次不必要的網路搜尋。
        web_results = (
            self.web_searcher.search(normalized)
            if not hits and not suggestions and self.web_searcher
            else []
        )
        tool_used = (
            "Embedding RAG 本地教學"
            if hits and self.retriever.embedder
            else "RAG 本地教學"
            if hits
            else "Embedding RAG 相近教學"
            if suggestions and self.retriever.embedder
            else "RAG 相近教學"
            if suggestions
            else "WebSearch 公開參考"
            if web_results
            else "Embedding RAG + WebSearch"
            if self.retriever.embedder
            else "RAG + WebSearch"
        )
        agent_status = (
            "已找到本地教學"
            if hits
            else "找到相近教學，等待使用者確認"
            if suggestions
            else "本地沒有對應教學，已嘗試公開參考"
            if web_results
            else "目前沒有找到可用資料"
        )
        message = (
            "找到這些教學，請選最接近你想做的事。"
            if hits
            else "可能是這些教學，請選最接近你想做的事。"
            if suggestions
            else (
                "目前還沒有找到合適的教學。這一版先提供 iPhone 與 iPhone 上的 LINE，"
                "可以試試「字太小」或「螢幕太暗」。"
            )
        )
        if web_results:
            message = "本地還沒有這份教學，先提供網路參考；請注意版本與來源。"
        return SearchResponse(
            message=message,
            hits=hits,
            suggestions=suggestions,
            web_results=web_results,
            interpreted_query=normalized,
            tool_used=tool_used,
            agent_status=agent_status,
        )

    @staticmethod
    def view(session: Session) -> SessionView:
        completed = session.status == "completed"
        total = len(session.guide.steps)
        return SessionView(
            **session.model_dump(),
            total_steps=total,
            current_step=None if completed else session.guide.steps[session.step_index],
            completed_steps=total if completed else session.step_index,
        )

    def start(self, guide_id: str, platform: str) -> SessionView:
        guide = self.knowledge.get(guide_id)
        if guide.platform != platform:
            raise ValueError("這份教學與選擇的手機不符。")
        session = Session(id=str(uuid4()), guide=guide)
        self.store.create(session)
        return self.view(session)

    def get(self, session_id: str) -> SessionView:
        return self.view(self.store.get(session_id))

    def act(self, session_id: str, request: ActionRequest) -> SessionView:
        # 進度圖一次只處理一個動作，revision 防止多分頁覆蓋彼此的進度。
        session = self.store.get(session_id)
        if session.revision != request.expected_revision:
            raise ConflictError("進度已更新，已替你保留最新的一步。")
        result = self.progress_graph.invoke({"session": session, "action": request.action})
        updated = result["session"].model_copy(update={"revision": session.revision + 1})
        self.store.update(updated, request.expected_revision)
        return self.view(updated)

    def help(self, session_id: str, question: str) -> HelpResponse:
        session = self.store.get(session_id)
        if session.status == "completed":
            raise ValueError("教學已完成，請先選擇重新練習。")
        return self.help_graph.invoke({"session": session, "question": question})["result"]
