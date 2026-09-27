from __future__ import annotations

import json
from pathlib import Path


def test_source_lock_has_ten_unique_pinned_sources() -> None:
    data = json.loads(Path("sources.lock.json").read_text())
    sources = data["sources"]
    assert len(sources) == 10
    assert len({item["name"] for item in sources}) == 10
    assert len({item["path"] for item in sources}) == 10
    assert all(len(item["commit"]) == 40 for item in sources)
    assert all(item["path"].startswith("upstream/") for item in sources)
