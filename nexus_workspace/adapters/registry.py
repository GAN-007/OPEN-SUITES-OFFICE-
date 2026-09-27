from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..models import EngineName
from .base import EngineAdapter
from .cli import CliAdapter
from .http import JsonHttpAdapter
from .mcp import McpHttpAdapter
from .pageindex import PageIndexAdapter


class AdapterRegistry:
    def __init__(self, settings: Settings, root: Path | None = None):
        root = root or Path.cwd()
        timeout = float(settings.execution_timeout_seconds)
        self.adapters: dict[EngineName, EngineAdapter] = {
            EngineName.GENOFFICE: CliAdapter(EngineName.GENOFFICE, settings.command_for(EngineName.GENOFFICE), timeout, root),
            EngineName.OPENMAIC: JsonHttpAdapter(EngineName.OPENMAIC, settings.endpoint_for(EngineName.OPENMAIC), timeout),
            EngineName.WEKNORA: JsonHttpAdapter(EngineName.WEKNORA, settings.endpoint_for(EngineName.WEKNORA), timeout),
            EngineName.GRAPHITI: McpHttpAdapter(EngineName.GRAPHITI, settings.endpoint_for(EngineName.GRAPHITI), timeout),
            EngineName.COGNEE: JsonHttpAdapter(EngineName.COGNEE, settings.endpoint_for(EngineName.COGNEE), timeout),
            EngineName.BROWSER_USE: CliAdapter(EngineName.BROWSER_USE, settings.command_for(EngineName.BROWSER_USE), timeout, root),
            EngineName.OPEN_WEBUI: JsonHttpAdapter(EngineName.OPEN_WEBUI, settings.endpoint_for(EngineName.OPEN_WEBUI), timeout),
            EngineName.PAGEINDEX: PageIndexAdapter(root / "upstream/pageindex"),
            EngineName.AGENT_REACH: CliAdapter(EngineName.AGENT_REACH, settings.command_for(EngineName.AGENT_REACH), timeout, root / "upstream/agent-reach"),
            EngineName.QWEN_AUDIO_AGENT: JsonHttpAdapter(EngineName.QWEN_AUDIO_AGENT, settings.endpoint_for(EngineName.QWEN_AUDIO_AGENT), timeout),
        }

    def get(self, engine: EngineName) -> EngineAdapter:
        return self.adapters[engine]
