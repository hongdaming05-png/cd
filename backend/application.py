"""Composition root: assemble dependencies and register the HTTP layer."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import register_exception_handlers
from backend.api.router import router
from backend.config import Settings
from backend.llm.factory import create_explainer
from backend.llm.search_agent import SearchAgent
from backend.rag.knowledge import KnowledgeBase
from backend.rag.semantic import OllamaEmbedder
from backend.repositories import SessionStore
from backend.services import GuideService
from backend.speech import configure_speech
from backend.web import WebSearcher


def create_app(settings: Settings | None = None) -> FastAPI:
    # 這是後端的組裝中心：設定決定要使用哪個模型、檢索器和資料庫。
    settings = settings or Settings()
    configure_speech(settings.speech_provider)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 服務只建立一次；教學 JSON 與 embedding 也在這裡載入／建立索引。
        app.state.service = GuideService(
            KnowledgeBase(settings.content_dir),
            SessionStore(settings.database_path),
            create_explainer(settings),
            SearchAgent(settings) if settings.llm_provider == "ollama" else None,
            WebSearcher(),
            OllamaEmbedder(settings.llm_base_url, settings.embedding_model, settings.llm_timeout)
            if settings.llm_provider == "ollama"
            else None,
        )
        yield

    app = FastAPI(title="慢慢來 API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    register_exception_handlers(app)
    app.include_router(router)
    return app
