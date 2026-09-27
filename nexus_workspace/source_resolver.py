from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import EngineName


class EngineSourceMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class EngineSourceResolver:
    root: Path
    mode: str = "vendored"
    vendor_dir: Path = Path("engines")
    upstream_dir: Path = Path("upstream")

    def _vendor_path(self, engine: EngineName) -> Path:
        return self.root / self.vendor_dir / engine.value

    def _upstream_path(self, engine: EngineName) -> Path:
        return self.root / self.upstream_dir / engine.value

    def resolve(self, engine: EngineName) -> Path:
        vendor = self._vendor_path(engine)
        upstream = self._upstream_path(engine)

        if self.mode == "vendored":
            if vendor.exists():
                return vendor
            raise EngineSourceMissing(
                f"Vendored source for {engine.value} is missing at {vendor}. "
                "Run scripts/vendor_upstreams.py after initializing the pinned sources."
            )
        if self.mode == "upstream":
            if upstream.exists():
                return upstream
            raise EngineSourceMissing(
                f"Pinned upstream source for {engine.value} is missing at {upstream}. "
                "Initialize submodules first."
            )
        if self.mode == "auto":
            if vendor.exists():
                return vendor
            if upstream.exists():
                return upstream
            raise EngineSourceMissing(
                f"No source tree for {engine.value}; checked {vendor} and {upstream}."
            )
        raise ValueError(f"Unsupported engine source mode: {self.mode}")

    def status(self, engine: EngineName) -> dict[str, str | bool]:
        vendor = self._vendor_path(engine)
        upstream = self._upstream_path(engine)
        try:
            selected = self.resolve(engine)
        except EngineSourceMissing:
            selected = vendor if self.mode == "vendored" else upstream
        return {
            "engine": engine.value,
            "mode": self.mode,
            "vendor_path": str(vendor),
            "vendor_available": vendor.exists(),
            "upstream_path": str(upstream),
            "upstream_available": upstream.exists(),
            "selected_path": str(selected),
            "selected_available": selected.exists(),
        }
