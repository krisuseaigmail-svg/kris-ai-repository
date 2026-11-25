"""测试库隔离。禁止连到本机 5432 上的客户交付台账，也禁止删掉已有的库 ledger。"""

from __future__ import annotations

import os

from sqlalchemy.engine import make_url

DEFAULT_DATABASE_URL = "postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:5433/asset_ledger_test"
_CREATED_HERE: set[str] = set()


def database_url() -> str:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        raw = DEFAULT_DATABASE_URL
        os.environ["DATABASE_URL"] = raw
    return raw


def assert_isolated_database(url: str | None = None) -> None:
    parsed = make_url(url or database_url())
    port = parsed.port or 5432
    if port == 5432:
        raise RuntimeError(
            "测试拒绝使用端口 5432，以免连到客户交付台账。"
            "请指向独立实例，默认是 127.0.0.1:5433 上的库 asset_ledger_test。"
        )
    if parsed.database in {"ledger", "asset_ledger"}:
        raise RuntimeError("测试库名不能是现场库 ledger 或 asset_ledger")


def remember_created(name: str) -> None:
    _CREATED_HERE.add(name)


def created_here(name: str) -> bool:
    return name in _CREATED_HERE


def forget_created(name: str) -> None:
    _CREATED_HERE.discard(name)
