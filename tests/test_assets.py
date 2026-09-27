from pathlib import Path

from nexus_workspace.assets import AssetStore


def test_assets_are_immutable_versioned_and_hashed(temp_db, tmp_path: Path) -> None:
    store = AssetStore(temp_db, tmp_path / "artifacts")
    first = store.create(name="report.docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", content=b"version-one", actor="tester")
    second = store.add_version(first.asset_id, content=b"version-two", actor="tester")
    assert first.version == 1
    assert second.version == 2
    assert first.sha256 != second.sha256
    assert Path(first.path).read_bytes() == b"version-one"
    assert Path(second.path).read_bytes() == b"version-two"
