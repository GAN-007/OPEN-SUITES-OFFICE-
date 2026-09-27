from __future__ import annotations

from pathlib import Path

import pytest

from nexus_workspace.database import Database


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    return Database(tmp_path / "nexus.db")
