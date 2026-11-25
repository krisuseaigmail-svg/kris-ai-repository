from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_spaces_root_name ON spaces (lower(name)) WHERE parent_id IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_spaces_child_name ON spaces (parent_id, lower(name)) WHERE parent_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_assets_code ON assets (lower(code))",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_assets_serial ON assets (lower(serial))",
    "CREATE INDEX IF NOT EXISTS ix_spaces_parent ON spaces (parent_id)",
    "CREATE INDEX IF NOT EXISTS ix_assets_location_space ON assets (location_space_id)",
    "CREATE INDEX IF NOT EXISTS ix_assets_mounted ON assets (mounted_asset_id)",
)


class SchemaMigration(Base):
    __tablename__ = "schema_migration"

    version: Mapped[str] = mapped_column(String(32), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("spaces.id", name="fk_spaces_parent", ondelete="RESTRICT"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rack_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    serial: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bmc_ip: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    biz_ip: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    mac: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)
    location_space_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("spaces.id", name="fk_assets_location_space", ondelete="RESTRICT"),
        nullable=True,
    )
    mounted_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", name="fk_assets_mounted", ondelete="RESTRICT"),
        nullable=True,
    )
    start_u: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_u: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location_note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def ensure_indexes(bound_engine) -> None:
    with bound_engine.begin() as conn:
        for statement in INDEX_SQL:
            conn.execute(text(statement))
