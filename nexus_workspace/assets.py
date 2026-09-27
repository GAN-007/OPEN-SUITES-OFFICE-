from __future__ import annotations

import hashlib
from pathlib import Path

from .database import Database
from .models import AssetVersion


class AssetStore:
    def __init__(self, db: Database, root: Path):
        self.db = db
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, *, name: str, media_type: str, content: bytes, actor: str) -> AssetVersion:
        asset = self.db.create_asset(name, media_type)
        return self.add_version(asset.id, content=content, actor=actor)

    def add_version(self, asset_id: str, *, content: bytes, actor: str) -> AssetVersion:
        asset = self.db.asset(asset_id)
        if asset is None:
            raise KeyError(asset_id)
        version = self.db.next_asset_version(asset_id)
        digest = hashlib.sha256(content).hexdigest()
        directory = self.root / asset_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"v{version}-{edigest[:16]}"
        path.write_bytes(content)
        row = self.db.add_asset_version(
            asset_id=asset_id,
            version=version,
            sha256=digest,
            size=len(content),
            path=str(path),
            actor=actor,
        )
        return AssetVersion(
            asset_id=asset.id,
            version_id=row.id,
            version=row.version,
            name=asset.name,
            media_type=asset.media_type,
            sha256=row.sha256,
            size=row.size,
            path=row.path,
            created_at=row.created_at.isoformat(),
            actor=row.actor,
        )
