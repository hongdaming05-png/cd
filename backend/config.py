from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py 位於 backend 根部，往上一層就是專案根目錄。
ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EG_", env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    content_dir: Path = ROOT / "content" / "guides"
    database_path: Path = ROOT / ".data" / "sessions.sqlite3"
    speech_provider: Literal["sensevoice", "whisper"] = "sensevoice"
    llm_provider: Literal["none", "ollama", "compatible"] = "none"
    llm_model: str = "qwen2.5:7b"
    embedding_model: str = "bge-m3"
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_api_key: SecretStr = SecretStr("")
    llm_timeout: float = Field(default=25, ge=1, le=120)

    @model_validator(mode="after")
    def validate_llm(self):
        if self.llm_provider != "none" and not self.llm_model.strip():
            raise ValueError("啟用模型前，請設定 EG_LLM_MODEL")
        if not self.llm_base_url.startswith(("http://", "https://")):
            raise ValueError("EG_LLM_BASE_URL 必須是 HTTP(S) 網址")
        return self
