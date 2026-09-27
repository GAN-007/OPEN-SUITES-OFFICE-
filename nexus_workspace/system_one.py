from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .models import EngineName

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SystemOneSignal:
    engine: EngineName
    confidence: float
    answers: dict[str, Any]
    routing: dict[str, Any] | None
    latency_ms: int


class SystemOneDecisionPlane:
    """Fail-open Laya/Jev-compatible System-One client.

    Nexus remains authoritative for explicit capability/engine choices and for
    every approval/provenance rule. In shadow mode this class only emits
    comparable routing evidence. In assist mode the router may use a
    high-confidence System-One engine choice only when deterministic routing
    has no specialist match.
    """

    VALID_MODES = {"off", "shadow", "assist"}

    def __init__(
        self,
        *,
        mode: str = "off",
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 1.5,
        confidence_threshold: float = 0.85,
    ) -> None:
        normalized = (mode or "off").strip().lower()
        if normalized not in self.VALID_MODES:
            raise ValueError(f"Unsupported System-One mode: {mode!r}")
        self.mode = normalized
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.confidence_threshold = min(1.0, max(0.0, float(confidence_threshold)))

    @property
    def enabled(self) -> bool:
        return self.mode != "off" and bool(self.base_url)

    def classify(self, intent: str) -> SystemOneSignal | None:
        if not self.enabled:
            return None

        questions = {
            "primary_engine": {
                "type": "choice",
                "instructions": "Which Nexus specialist engine should primarily own this request?",
                "criteria": {
                    "genoffice": "Office documents, PDF, spreadsheet, slides, Markdown or HTML editing",
                    "openmaic": "Teaching, classroom, course, quiz, lesson, whiteboard or project-based learning",
                    "weknora": "Enterprise knowledge base, wiki, RAG or workspace knowledge",
                    "graphiti": "Temporal facts, timelines, historical state or time-varying knowledge",
                    "cognee": "Durable memory, recall, preferences or learned project/user context",
                    "browser-use": "Stateful browser interaction, navigation, login, forms, clicks or screenshots",
                    "open-webui": "General model/chat workspace when no specialist engine is the primary owner",
                    "pageindex": "Long-document structural retrieval, sections, appendices or hierarchical document reasoning",
                    "agent-reach": "Internet research or source-specific acquisition such as GitHub, Reddit, YouTube or LinkedIn",
                    "qwen-audio-agent": "Realtime voice, microphone, listening, speaking or audio interaction",
                },
            },
            "needs_browser": {
                "type": "noul",
                "instructions": "Does this request require stateful browser interaction?",
            },
            "needs_memory": {
                "type": "noul",
                "instructions": "Does this request require durable cross-session memory?",
            },
            "needs_retrieval": {
                "type": "noul",
                "instructions": "Does this request require knowledge or document retrieval?",
            },
            "needs_audio": {
                "type": "noul",
                "instructions": "Does this request require realtime audio or voice interaction?",
            },
        }
        payload = {
            "state": {
                "request": intent,
                "policy": {
                    "explicit_nexus_overrides_remain_authoritative": True,
                    "side_effect_approval_remains_authoritative": True,
                    "system_one_is_advisory": True,
                },
            },
            "questions": questions,
        }
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"

        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url}/v1/systemone",
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            body = response.json()
            answers = body.get("answers")
            if not isinstance(answers, dict):
                raise ValueError("System-One response has no answers object")
            primary = answers.get("primary_engine")
            if not isinstance(primary, dict):
                raise ValueError("System-One response has no primary_engine answer")
            choice = primary.get("choice")
            engine = EngineName(choice)
            probabilities = primary.get("probabilities") or {}
            confidence = float(primary.get("confidence", probabilities.get(choice, 0.0)) or 0.0)
            signal = SystemOneSignal(
                engine=engine,
                confidence=confidence,
                answers=answers,
                routing=body.get("routing") if isinstance(body.get("routing"), dict) else None,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            logger.info(
                "nexus_system_one_decision",
                extra={
                    "mode": self.mode,
                    "engine": signal.engine.value,
                    "confidence": signal.confidence,
                    "latency_ms": signal.latency_ms,
                },
            )
            return signal
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            logger.warning("Nexus System-One failed open: %s", exc)
            return None
