from nexus_workspace.models import EngineName, RouteRequest
from nexus_workspace.routing import CapabilityRouter
from nexus_workspace.system_one import SystemOneSignal


class FakeDecisionPlane:
    def __init__(self, *, mode: str, engine: EngineName, confidence: float):
        self.mode = mode
        self.confidence_threshold = 0.85
        self.signal = SystemOneSignal(
            engine=engine,
            confidence=confidence,
            answers={},
            routing={"model": "test"},
            latency_ms=1,
        )
        self.calls: list[str] = []

    def classify(self, intent: str):
        self.calls.append(intent)
        return self.signal


def test_shadow_system_one_never_replaces_deterministic_owner() -> None:
    plane = FakeDecisionPlane(mode="shadow", engine=EngineName.BROWSER_USE, confidence=0.99)
    result = CapabilityRouter(decision_plane=plane).route(
        RouteRequest(intent="Compare appendix C in this long document")
    )
    assert result.engine == EngineName.PAGEINDEX
    assert plane.calls


def test_assist_system_one_can_resolve_only_ambiguous_default_route() -> None:
    plane = FakeDecisionPlane(mode="assist", engine=EngineName.BROWSER_USE, confidence=0.95)
    result = CapabilityRouter(decision_plane=plane).route(
        RouteRequest(intent="Do the thing for the customer")
    )
    assert result.engine == EngineName.BROWSER_USE
    assert "System-One assist" in result.reason


def test_assist_system_one_cannot_override_explicit_engine() -> None:
    plane = FakeDecisionPlane(mode="assist", engine=EngineName.BROWSER_USE, confidence=0.99)
    result = CapabilityRouter(decision_plane=plane).route(
        RouteRequest(
            intent="Do the thing",
            preferred_engine=EngineName.GENOFFICE,
        )
    )
    assert result.engine == EngineName.GENOFFICE
    assert plane.calls == []


def test_low_confidence_system_one_keeps_general_fallback() -> None:
    plane = FakeDecisionPlane(mode="assist", engine=EngineName.BROWSER_USE, confidence=0.50)
    result = CapabilityRouter(decision_plane=plane).route(
        RouteRequest(intent="Do the thing for the customer")
    )
    assert result.engine == EngineName.OPEN_WEBUI
