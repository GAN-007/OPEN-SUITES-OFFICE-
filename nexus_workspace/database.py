from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class ProvenanceRecord(Base):
    __tablename__ = "provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    engine: Mapped[str] = mapped_column(String(100), index=True)
    capability: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(300))
    request_json: Mapped[dict] = mapped_column(JSON)
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AssetRecord(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    media_type: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AssetVersionRecord(Base):
    __tablename__ = "asset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(String(1000))
    actor: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{path}", future=True)
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return Session(self.engine)

    def add_provenance(
        self,
        *,
        execution_id: str,
        actor: str,
        engine: str,
        capability: str,
        action: str,
        request_json: dict,
        result_json: dict,
    ) -> ProvenanceRecord:
        record = ProvenanceRecord(
            id=str(uuid4()),
            execution_id=execution_id,
            actor=actor,
            engine=engine,
            capability=capability,
            action=action,
            request_json=request_json,
            result_json=result_json,
        )
        with self.session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record

    def provenance(self, record_id: str) -> ProvenanceRecord | None:
        with self.session() as session:
            return session.get(ProvenanceRecord, record_id)

    def create_asset(self, name: str, media_type: str) -> AssetRecord:
        record = AssetRecord(id=str(uuid4()), name=name, media_type=media_type)
        with self.session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record

    def asset(self, asset_id: str) -> AssetRecord | None:
        with self.session() as session:
            return session.get(AssetRecord, asset_id)

    def next_asset_version(self, asset_id: str) -> int:
        with self.session() as session:
            rows = session.scalars(
                select(AssetVersionRecord).where(AssetVersionRecord.asset_id == asset_id)
            ).all()
            return max((row.version for row in rows), default=0) + 1

    def add_asset_version(
        self,
        *,
        asset_id: str,
        version: int,
        sha256: str,
        size: int,
        path: str,
        actor: str,
    ) -> AssetVersionRecord:
        record = AssetVersionRecord(
            id=str(uuid4()),
            asset_id=asset_id,
            version=version,
            sha256=sha256,
            size=size,
            path=path,
            actor=actor,
        )
        with self.session() as session:
            session.add(record)
            session.commit()
            session.refresh(record)
        return record
