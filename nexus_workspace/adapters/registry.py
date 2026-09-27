from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..models import EngineName
from ..source_resolver import EngineSourceResolver
from .base import EngineAdapter
from .cli import CliAdapter
from .http import JsonHttpAdapter
from .mcp import McpHttpAdapter
from .pageindex import PageIndexAdapter


class AdapterRegistry:
    def __init__(self, settings: Settings, root: Path | None = None):
        root = root or Path.cwd()
        timeout = float(settings.execution_timeout_seconds)
        sources = EngineSourceResolver(
            root=root,
            mode=settings.engine_source_mode,
            vendor_dir=settings.engine_dir,
            upstream_dir=settings.upstream_dir,
        )

        genoffice_root = sources.resolve(EngineName.GENOFFICE)
        browser_use_root = sources.resolve(EngineName.BROWSER_USE)
        pageindex_root = sources.resolve(EngineName.PAGEINDEX)
        agent_reach_root = sources.resolve(EngineName.AGENT_REACH)

        self.adapters: dict[EngineName, EngineAdapter] = {
            EngineName.GENOFFICE: CliAdapter(
                EngineName.GENOFFICE,
                settings.command_for(EngineName.GENOFFICE),
                timeout,
                genoffice_root,
            ),
            EngineName.OPENMAIC: JsonHttpAdapter(
                EngineName.OPENMAIC,
                settings.endpoint_for(EngineName.OPENMAIC),
                timeout,
            ),
            EngineName.WEKNORA: JsonHttpAdapter(
                EngineName.WEKNORA,
                settings.endpoint_for(EngineName.WEKNORA),
                timeout,
            ),
            EngineName.GRAPHITI: McpHttpAdapter(
                EngineName.GRAPHITI,
                settings.endpoint_for(EngineName.GRAPHITI),
                timeout,
            ),
            EngineName.COGNEE: JsonHttpAdapter(
                EngineName.COGNEE,
                settings.endpoint_for(EngineName.COGNEE),
                timeout,
            ),
            EngineName.BROWSER_USE: CliAdapter(
                EngineName.BROWSER_USE,
                settings.command_for(EngineName.BROWSER_USE),
                timeout,
                browser_use_root,
            ),
            EngineName.OPEN_WEBUI: JsonHttpAdapter(
                EngineName.OPEN_WEBUI,
                settings.endpoint_for(EngineName.OPEN_WEBUI),
                timeout,
            ),
            EngineName.PAGEINDEX: PageIndexAdapter(pageindex_root),
            EngineName.AGENT_REACH: CliAdapter(
                EngineName.AGENT_REACH,
                settings.command_for(EngineName.AGENT_REACH),
                timeout,
                agent_reach_root,
            ),
            EngineName.QWEN_AUDIO_AGENT: JsonHttpAdapter(
                EngineName.QWEN_AUDIO_AGENT,
                settings.endpoint_for(EngineName.QWEN_AUDIO_AGENT),
                timeout,
            ),
        }

    def get(self, engine: EngineName) -> EngineAdapter:
        return self.adapters[engine]
