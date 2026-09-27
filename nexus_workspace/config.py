from __future__ import annotations

import shlex
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import EngineName


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEXUS_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8787
    state_db: Path = Path("state/nexus.db")
    artifact_dir: Path = Path("artifacts")
    execution_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    require_approval_for_side_effects: bool = True

    # Optional Laya/Jev-compatible System-One decision plane.
    # off: disabled; shadow: observe only; assist: resolve ambiguous fallback routes only.
    system_one_mode: str = "off"
    system_one_base_url: str | None = None
    system_one_api_key: str | None = None
    system_one_timeout_seconds: float = Field(default=1.5, ge=0.1, le=30)
    system_one_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    openmaic_url: str | None = None
    weknora_url: str | None = None
    graphiti_mcp_url: str | None = None
    cognee_url: str | None = None
    open_webui_url: str | None = None
    qwen_audio_url: str | None = None

    genoffice_command: str | None = None
    agent_reach_command: str | None = None
    browser_use_command: str | None = None
    qwen_audio_command: str | None = None

    def command_for(self, engine: EngineName) -> list[str] | None:
        raw = {
            EngineName.GENOFFICE: self.genoffice_command,
            EngineName.AGENT_REACH: self.agent_reach_command,
            EngineName.BROWSER_USE: self.browser_use_command,
            EngineName.QWEN_AUDIO_AGENT: self.qwen_audio_command,
        }.get(engine)
        return shlex.split(raw) if raw else None

    def endpoint_for(self, engine: EngineName) -> str | None:
        return {
            EngineName.OPENMAIC: self.openmaic_url,
            EngineName.WEKNORA: self.weknora_url,
            EngineName.GRAPHITI: self.graphiti_mcp_url,
            EngineName.COGNEE: self.cognee_url,
            EngineName.OPEN_WEBUI: self.open_webui_url,
            EngineName.QWEN_AUDIO_AGENT: self.qwen_audio_url,
        }.get(engine)
