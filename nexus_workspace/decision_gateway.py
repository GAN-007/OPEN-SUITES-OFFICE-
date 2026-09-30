from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

RequestFn = Callable[["ProviderEndpoint", dict[str, Any], float], dict[str, Any]]


class DecisionPlaneNotConfigured(RuntimeError):
    pass


class DecisionPlaneUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderEndpoint:
    name: str
    base_url: str
    api_key: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.base_url.strip())


class GanDecisionPlane:
    """Shared Jev-compatible System-One gateway for GAN projects.

    The gateway does not make domain decisions itself. It validates and forwards
    the typed System-One contract to an explicitly configured provider, with an
    optional provider fallback. Application-level authorization, approvals,
    domain policy and side-effect controls remain owned by each calling project.
    """

    SUPPORTED_PROVIDERS = {"laya", "jev"}

    def __init__(
        self,
        *,
        primary_provider: str,
        fallback_provider: str | None,
        laya_base_url: str | None,
        laya_api_key: str | None,
        jev_base_url: str | None,
        jev_api_key: str | None,
        timeout_seconds: float,
        request_fn: RequestFn | None = None,
    ) -> None:
        self.primary_provider = self._normalize_provider(primary_provider)
        self.fallback_provider = (
            self._normalize_provider(fallback_provider)
            if fallback_provider and fallback_provider.strip()
            else None
        )
        if self.fallback_provider == self.primary_provider:
            self.fallback_provider = None

        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.providers = {
            "laya": ProviderEndpoint(
                name="laya",
                base_url=(laya_base_url or "").rstrip("/"),
                api_key=(laya_api_key or "").strip(),
            ),
            "jev": ProviderEndpoint(
                name="jev",
                base_url=(jev_base_url or "").rstrip("/"),
                api_key=(jev_api_key or "").strip(),
            ),
        }
        self._request_fn = request_fn or self._post_json

    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        provider = (value or "").strip().lower()
        if provider not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported System-One provider {value!r}; "
                f"expected one of {sorted(cls.SUPPORTED_PROVIDERS)}"
            )
        return provider

    def provider_order(self) -> list[ProviderEndpoint]:
        names = [self.primary_provider]
        if self.fallback_provider is not None:
            names.append(self.fallback_provider)
        return [self.providers[name] for name in names if self.providers[name].configured]

    def health(self) -> dict[str, Any]:
        configured = [provider.name for provider in self.provider_order()]
        return {
            "status": "ok" if configured else "unconfigured",
            "primary_provider": self.primary_provider,
            "fallback_provider": self.fallback_provider,
            "configured_order": configured,
            "providers": {
                name: {"configured": endpoint.configured}
                for name, endpoint in self.providers.items()
            },
        }

    @staticmethod
    def _post_json(
        provider: ProviderEndpoint,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        headers = {"content-type": "application/json", "accept": "application/json"}
        if provider.api_key:
            headers["authorization"] = f"Bearer {provider.api_key}"

        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.post(
                f"{provider.base_url}/v1/systemone",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()

        if not isinstance(body, dict):
            raise ValueError("System-One provider returned a non-object JSON response")
        answers = body.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("System-One provider response is missing an answers object")
        return body

    def decide(self, payload: dict[str, Any]) -> dict[str, Any]:
        providers = self.provider_order()
        if not providers:
            raise DecisionPlaneNotConfigured(
                "No configured System-One provider endpoint is available"
            )

        failures: list[str] = []
        started = time.perf_counter()

        for index, provider in enumerate(providers):
            provider_started = time.perf_counter()
            try:
                body = self._request_fn(provider, payload, self.timeout_seconds)
                result = dict(body)
                result["gateway"] = {
                    "service": "gan-decision-plane",
                    "provider": provider.name,
                    "fallback_used": index > 0,
                    "provider_latency_ms": int(
                        (time.perf_counter() - provider_started) * 1000
                    ),
                    "total_latency_ms": int((time.perf_counter() - started) * 1000),
                }
                return result
            except (httpx.HTTPError, ValueError, TypeError, RuntimeError) as exc:
                failures.append(f"{provider.name}:{exc.__class__.__name__}")

        raise DecisionPlaneUnavailable(
            "All configured System-One providers failed: " + ", ".join(failures)
        )
