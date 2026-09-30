from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EngineName(StrEnum):
    GENOFFICE = "genoffice"
    OPENMAIC = "openmaic"
    WEKNORA = "weknora"
    GRAPHITI = "graphiti"
    COGNEE = "cognee"
    BROWSER_USE = "browser-use"
    OPEN_WEBUI = "open-webui"
    PAGEINDEX = "pageindex"
    AGENT_REACH = "agent-reach"
    QWEN_AUDIO_AGENT = "qwen-audio-agent"


class Capability(StrEnum):
    OFFICE_DOCUMENTS = "office_documents"
    CLASSROOM = "classroom"
    ENTERPRISE_KNOWLEDGE = "enterprise_knowledge"
    TEMPORAL_KNOWLEDGE = "temporal_knowledge"
    MEMORY = "memory"
    BROWSER_AUTOMATION = "browser_automation"
    AI_WORKSPACE = "ai_workspace"
    LONG_DOCUMENT_RETRIEVAL = "long_document_retrieval"
    INTERNET_RESEARCH = "internet_research"
    REALTIME_VOICE = "realtime_voice"


class RiskLevel(StrEnum):
    READ = "read"
    WRITE = "write"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"


class RouteRequest(BaseModel):
    intent: str = Field(min_length=1)
    capability: Capability | None = None
    preferred_engine: EngineName | None = None


class RouteDecision(BaseModel):
    engine: EngineName
    capability: Capability
    reason: str


class ExecuteRequest(BaseModel):
    intent: str = Field(min_length=1)
    action: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    capability: Capability | None = None
    engine: EngineName | None = None
    risk: RiskLevel = RiskLevel.READ
    approved: bool = False
    actor: str = "local-user"


class ExecuteResult(BaseModel):
    execution_id: str
    engine: EngineName
    capability: Capability
    action: str
    result: Any
    provenance_id: str


class AssetCreate(BaseModel):
    name: str = Field(min_length=1)
    media_type: str = "application/octet-stream"
    content_base64: str
    actor: str = "local-user"


class AssetVersion(BaseModel):
    asset_id: str
    version_id: str
    version: int
    name: str
    media_type: str
    sha256: str
    size: int
    path: str
    created_at: str
    actor: str


class EngineStatus(BaseModel):
    engine: EngineName
    configured: bool
    transport: str
    endpoint: str | None = None
    command: list[str] | None = None


class SystemOneQuestion(BaseModel):
    type: str
    instructions: str | None = None
    criteria: dict[str, str] | list[str] | None = None

    @classmethod
    def _allowed_types(cls) -> set[str]:
        return {"choice", "score", "noul"}

    def model_post_init(self, __context: Any) -> None:
        if self.type not in self._allowed_types():
            raise ValueError("System-One question type must be choice, score, or noul")
        if self.type == "choice":
            if not isinstance(self.criteria, dict) or not self.criteria:
                raise ValueError("choice questions require a non-empty criteria object")
        elif self.type == "score":
            if not isinstance(self.criteria, list) or not self.criteria:
                raise ValueError("score questions require a non-empty criteria list")
        elif self.criteria is not None and not isinstance(self.criteria, (dict, list)):
            raise ValueError("noul criteria must be omitted, a list, or an object")


class SystemOneGatewayRequest(BaseModel):
    state: Any
    questions: dict[str, SystemOneQuestion] = Field(min_length=1, max_length=100)
