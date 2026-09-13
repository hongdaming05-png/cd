from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

Text = Annotated[str, Field(min_length=1, max_length=1000)]
Platform = Literal["ios", "android"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Source(Model):
    title: Text
    url: HttpUrl
    checked_at: date


class Illustration(Model):
    screen: Text
    target: Text
    kind: Literal["app", "row", "slider", "toggle", "choice"] = "row"
    rows: list[Text] = Field(default_factory=list, max_length=5)


class FAQ(Model):
    question: Text
    answer: Text


class Step(Model):
    title: Text
    instruction: Text
    hint: Text
    checkpoint: Text
    illustration: Illustration


class Guide(Model):
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    revision: int = Field(ge=1)
    title: Text
    summary: Text
    platform: Platform
    app: Literal["iphone", "line"]
    version_note: Text
    estimated_minutes: int = Field(ge=1, le=30)
    icon: str
    aliases: list[Text] = Field(min_length=1)
    prerequisites: list[Text] = Field(min_length=1)
    outcome: Text
    sources: list[Source] = Field(min_length=1)
    steps: list[Step] = Field(min_length=1, max_length=30)
    faqs: list[FAQ] = Field(default_factory=list)


class SearchRequest(Model):
    query: str = Field(min_length=1, max_length=200)
    platform: Platform = "ios"


class SearchHit(Model):
    guide: Guide
    score: float


class SearchResponse(Model):
    message: str
    hits: list[SearchHit]
    suggestions: list[SearchHit] = Field(default_factory=list)
    web_results: list["WebResult"] = Field(default_factory=list)
    interpreted_query: str = ""
    tool_used: str = ""
    agent_status: str = ""


class WebResult(Model):
    title: Text
    url: HttpUrl
    snippet: Text


class StartRequest(Model):
    guide_id: str = Field(min_length=1, max_length=100)
    platform: Platform = "ios"


class Session(Model):
    id: str
    guide: Guide
    step_index: int = Field(default=0, ge=0)
    status: Literal["active", "completed"] = "active"
    revision: int = Field(default=0, ge=0)


class SessionView(Session):
    current_step: Step | None
    completed_steps: int
    total_steps: int


class ActionRequest(Model):
    action: Literal["next", "back", "restart"]
    expected_revision: int = Field(ge=0)


class HelpRequest(Model):
    question: str = Field(default="這一步我找不到，請幫幫我", min_length=1, max_length=300)


class Passage(Model):
    id: str
    text: str


class HelpResponse(Model):
    answer: str
    mode: Literal["reference", "ai", "fallback", "unsupported"]
    passages: list[Passage]
    sources: list[Source]


class ModelAnswer(Model):
    answer: str = Field(min_length=1, max_length=500)
    evidence_ids: list[str] = Field(min_length=1, max_length=5)
