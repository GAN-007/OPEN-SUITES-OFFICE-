from __future__ import annotations

import pytest
from pydantic import ValidationError

from nexus_workspace.decision_gateway import (
    DecisionPlaneNotConfigured,
    GanDecisionPlane,
    ProviderEndpoint,
)
from nexus_workspace.models import SystemOneGatewayRequest


def make_gateway(request_fn, *, laya_url="http://laya.test:8000", jev_url=""):
    return GanDecisionPlane(
        primary_provider="laya",
        fallback_provider="jev",
        laya_base_url=laya_url,
        laya_api_key="laya-key",
        jev_base_url=jev_url,
        jev_api_key="jev-key",
        timeout_seconds=1.0,
        request_fn=request_fn,
    )


def payload() -> dict:
    return SystemOneGatewayRequest(
        state={"text": "route this request"},
        questions={
            "intent": {
                "type": "choice",
                "instructions": "Choose a route",
                "criteria": {"support": "support request", "sales": "sales request"},
            },
            "urgent": {
                "type": "noul",
                "instructions": "Is this urgent?",
            },
        },
    ).model_dump(exclude_none=True)


def test_gateway_preserves_provider_answers_and_adds_gateway_metadata() -> None:
    def request_fn(provider: ProviderEndpoint, body: dict, timeout: float) -> dict:
        assert provider.name == "laya"
        assert provider.api_key == "laya-key"
        assert timeout == 1.0
        assert body["questions"]["intent"]["type"] == "choice"
        return {
            "answers": {
                "intent": {
                    "type": "choice",
                    "choice": "support",
                    "confidence": 0.96,
                    "probabilities": {"support": 0.96, "sales": 0.04},
                },
                "urgent": {"type": "noul", "noul": 0.22, "confidence": 0.78},
            },
            "routing": {"model": "english"},
            "usage": {"output_tokens": 0},
        }

    result = make_gateway(request_fn).decide(payload())
    assert result["answers"]["intent"]["choice"] == "support"
    assert result["gateway"]["provider"] == "laya"
    assert result["gateway"]["fallback_used"] is False


def test_gateway_fails_over_from_laya_to_jev_without_changing_contract() -> None:
    called: list[str] = []

    def request_fn(provider: ProviderEndpoint, body: dict, timeout: float) -> dict:
        called.append(provider.name)
        if provider.name == "laya":
            raise RuntimeError("primary unavailable")
        return {
            "answers": {
                "intent": {
                    "type": "choice",
                    "choice": "sales",
                    "confidence": 0.88,
                    "probabilities": {"sales": 0.88, "support": 0.12},
                }
            }
        }

    result = make_gateway(request_fn, jev_url="http://jev.test:9000").decide(payload())
    assert called == ["laya", "jev"]
    assert result["answers"]["intent"]["choice"] == "sales"
    assert result["gateway"]["provider"] == "jev"
    assert result["gateway"]["fallback_used"] is True


def test_gateway_refuses_unconfigured_provider_set() -> None:
    gateway = make_gateway(lambda provider, body, timeout: {}, laya_url="", jev_url="")
    with pytest.raises(DecisionPlaneNotConfigured):
        gateway.decide(payload())


def test_invalid_choice_contract_is_rejected_before_provider_call() -> None:
    with pytest.raises(ValidationError):
        SystemOneGatewayRequest(
            state={"text": "bad"},
            questions={
                "intent": {
                    "type": "choice",
                    "instructions": "Choose",
                }
            },
        )
