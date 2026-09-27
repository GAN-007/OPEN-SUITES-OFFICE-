from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..models import EngineName
from ..runtime import RuntimeCatalog
from .base import EngineAdapter
from .cli import CliAdapter
from .http import JsonHttpAdapter
from .mcp import McpHttpAdapter
from .pageindex import PageIndexAdapter


class AdapterRegistry:
    def __init__(self, settings: Settings, root: Path | None = None):
        root = (root or Path.cwd()).resolve()
        timeout = float(settings.execution_timeout_seconds)
        catalog = RuntimeCatalog(settings.runtime_manifest, root)

        def cli(engine: EngineName) -> CliAdapter:
            spec = catalog.spec(engine)
            command = settings.explicit_command_for(engine) or spec.cli
            return CliAdapter(engine, command, timeout, spec.root)

        qwen_endpoint = settings.endpoint_for(EngineName.QWEN_AUDIO_AGENT)
        qwen_adapter: EngineAdapter
        if qwen_endpoint:
            qwen_adapter = JsonHttpAdapter(
                EngineName.QWEN_AUDIO_AGENT,
                qwen_endpoint,
                timeout,
            )
        else:
            qwen_adapter = cli(EngineName.QWEN_AUDIO_AGENT)

        self.adapters: dict[EngineName, EngineAdapter] = {
            EngineName.GENOFFICE: cli(EngineName.GENOFFICE),
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
            EngineName.BROWSER_USE: cli(EngineName.BROWSER_USE),
            EngineName.OPEN_WEBUI: JsonHttpAdapter(
                EngineName.OPEN_WEBUI,
                settings.endpoint_for(EngineName.OPEN_WEBUI),
                timeout,
            ),
            EngineName.PAGEINDEX: PageIndexAdapter(catalog.spec(EngineName.PAGEINDEX).root),
            EngineName.AGENT_REACH: cli(EngineName.AGENT_REACH),
            EngineName.QWEN_AUDIO_AGENT: qwen_adapter,
        }

    def get(self, engine: EngineName) -> EngineAdapter:
        return self.adapters[engine]
