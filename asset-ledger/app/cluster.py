from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.db import database_url


def _refuse(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def _engine_for(database: str):
    url = make_url(database_url()).set(database=database)
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def assert_cluster_exclusive() -> None:
    """建表之前的跨库检查。失败时进程退出，不建表、不写 schema_migration。"""
    if os.environ.get("PRODUCT_CODE") != "asset-ledger":
        _refuse("PRODUCT_CODE 必须是 asset-ledger")

    admin = None
    opened = []
    try:
        try:
            admin = _engine_for("postgres")
            with admin.connect() as conn:
                names = list(
                    conn.execute(
                        text("SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate")
                    ).scalars()
                )
        except SystemExit:
            raise
        except Exception:
            _refuse("无法检查数据库卷归属")
        if "ledger" in names:
            _refuse("数据库卷与客户交付台账冲突")
        for name in names:
            extra = None
            try:
                extra = _engine_for(name)
                opened.append(extra)
                with extra.connect() as conn:
                    found = conn.execute(text("SELECT to_regclass('public.deliveries') IS NOT NULL")).scalar()
            except SystemExit:
                raise
            except Exception:
                _refuse("无法检查数据库卷归属")
            if found:
                _refuse("数据库卷与客户交付台账冲突")
    finally:
        for extra in opened:
            extra.dispose()
        if admin is not None:
            admin.dispose()
