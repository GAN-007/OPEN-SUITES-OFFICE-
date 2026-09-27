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
