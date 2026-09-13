from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EG_", env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    api_url: str = "http://127.0.0.1:8000"
    ui_host: str = "127.0.0.1"
    ui_port: int = Field(default=8080, ge=1, le=65535)
    storage_secret: str = ""


def storage_secret(settings: FrontendSettings) -> str:
    if settings.storage_secret:
        return settings.storage_secret
    # Stable local cookie secret: restarting the UI must preserve browser identity.
    import secrets

    path = ROOT / ".data" / "frontend-secret"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        try:
            with path.open("x", encoding="utf-8") as file:
                file.write(secrets.token_urlsafe(48))
        except FileExistsError:
            pass
    return path.read_text(encoding="utf-8")
