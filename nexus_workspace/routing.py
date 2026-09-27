from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system_one import SystemOneDecisionPlane

from .models import Capability, EngineName, RouteDecision, RouteRequest


@dataclass(frozen=True)
class EngineOwnership:
    capability: Capability
    engine: EngineName
    keywords: tuple[str, ...]
    reason: str


OWNERSHIP = (
    EngineOwnership(Capability.OFFICE_DOCUMENTS, EngineName.GENOFFICE, ("docx", "xlsx", "pptx", "pdf", "spreadsheet", "slide", "document", "office", "markdown", "html"), "GenOffice owns native Office/PDF/Markdown/HTML fidelity and editing."),
    EngineOwnership(Capability.CLASSROOM, EngineName.OPENMAIC, ("teach", "course", "classroom", "quiz", "lesson", "whiteboard", "curriculum", "pbl"), "OpenMAIC owns interactive classroom and course state."),
    EngineOwnership(Capability.ENTERPRISE_KNOWLEDGE, EngineName.WEKNORA, ("knowledge base", "wiki", "enterprise", "rag", "workspace", "kb"), "WeKnora owns enterprise knowledge bases, RAG and Wiki workflows."),
    EngineOwnership(Capability.TEMPORAL_KNOWLEDGE, EngineName.GRAPHITI, ("when", "before", "after", "history", "temporal", "changed", "valid at", "timeline"), "Graphiti owns time-varying facts and temporal graph queries."),
    EngineOwnership(Capability.MEMORY, EngineName.COGNEE, ("remember", "recall", "memory", "previous session", "preference", "learned"), "Cognee owns durable agent/user/project memory lifecycle."),
    EngineOwnership(Capability.BROWSER_AUTOMATION, EngineName.BROWSER_USE, ("click", "fill", "submit", "browser", "website", "navigate", "login", "tab", "screenshot"), "Browser Use owns stateful browser interaction and web actions."),
    EngineOwnership(Capability.AI_WORKSPACE, EngineName.OPEN_WEBUI, ("chat", "model", "workspace", "open webui", "prompt", "tool"), "Open WebUI owns the general self-hosted model and chat workspace."),
    EngineOwnership(Capability.LONG_DOCUMENT_RETRIEVAL, EngineName.PAGEINDEX, ("page", "appendix", "section", "long document", "report", "contract", "tree index"), "PageIndex owns reasoning-based hierarchical retrieval over long documents."),
    EngineOwnership(Capability.INTERNET_RESEARCH, EngineName.AGENT_REACH, ("search web", "reddit", "youtube", "linkedin", "twitter", "github", "rss", "research", "internet"), "Agent-Reach owns source-specific internet acquisition and fallback routing."),
    EngineOwnership(Capability.REALTIME_VOICE, EngineName.QWEN_AUDIO_AGENT, ("voice", "speak", "listen", "audio", "realtime", "real-time", "microphone"), "Qwen Audio Agent owns full-duplex realtime voice presence and task delegation."),
)


class CapabilityRouter:
    def __init__(self, decision_plane: "SystemOneDecisionPlane | None" = None):
        self.decision_plane = decision_plane

    def route(self, request: RouteRequest) -> RouteDecision:
        if request.capability is not None:
            owner = next(item for item in OWNERSHIP if item.capability == request.capability)
            if request.preferred_engine is not None:
                return RouteDecision(engine=request.preferred_engine, capability=request.capability, reason="Explicit engine override requested by caller.")
            return RouteDecision(engine=owner.engine, capability=owner.capability, reason=owner.reason)

        if request.preferred_engine is not None:
            owner = next(item for item in OWNERSHIP if item.engine == request.preferred_engine)
            return RouteDecision(engine=owner.engine, capability=owner.capability, reason="Explicit engine override requested by caller.")

        text = request.intent.casefold()
        scored: list[tuple[int, int, EngineOwnership]] = []
        for index, owner in enumerate(OWNERSHIP):
            score = sum(1 for keyword in owner.keywords if keyword in text)
            scored.append((score, -index, owner))
        score, _, owner = max(scored, key=lambda item: (item[0], item[1]))

        signal = self.decision_plane.classify(request.intent) if self.decision_plane is not None else None

        if score == 0:
            owner = next(item for item in OWNERSHIP if item.engine == EngineName.OPEN_WEBUI)
            if (
                signal is not None
                and getattr(self.decision_plane, "mode", "shadow") == "assist"
                and signal.confidence >= getattr(self.decision_plane, "confidence_threshold", 1.0)
                and signal.engine != EngineName.OPEN_WEBUI
            ):
                assisted_owner = next(item for item in OWNERSHIP if item.engine == signal.engine)
                return RouteDecision(
                    engine=assisted_owner.engine,
                    capability=assisted_owner.capability,
                    reason=(
                        "System-One assist resolved an otherwise ambiguous Nexus route "
                        f"with confidence {signal.confidence:.3f}. "
                        "Nexus approval and provenance rules remain authoritative."
                    ),
                )
            return RouteDecision(
                engine=owner.engine,
                capability=owner.capability,
                reason="No specialist signal detected; routed to the general AI workspace.",
            )
        return RouteDecision(engine=owner.engine, capability=owner.capability, reason=owner.reason)
