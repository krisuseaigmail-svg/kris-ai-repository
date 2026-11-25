import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.cluster import assert_cluster_exclusive
from app.main import boot
from tests.isolation import assert_isolated_database, created_here, forget_created, remember_created


def _admin():
    assert_isolated_database()
    url = make_url(os.environ["DATABASE_URL"]).set(database="postgres")
    return create_engine(url, isolation_level="AUTOCOMMIT", poolclass=NullPool)


def _exists(name: str) -> bool:
    admin = _admin()
    try:
        with admin.connect() as conn:
            return bool(
                conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}).scalar()
            )
    finally:
        admin.dispose()


def _deliveries_have_rows(name: str) -> bool:
    if not _exists(name):
        return False
    extra = create_engine(
        make_url(os.environ["DATABASE_URL"]).set(database=name),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    try:
        with extra.connect() as conn:
            found = conn.execute(text("SELECT to_regclass('public.deliveries') IS NOT NULL")).scalar()
            if not found:
                return False
            count = conn.execute(text("SELECT count(*) FROM public.deliveries")).scalar()
            return bool(count)
    except Exception:
        return True
    finally:
        extra.dispose()


def _drop_database(name: str) -> None:
    assert_isolated_database()
    if name == "ledger" and not created_here(name):
        raise RuntimeError("拒绝删除并非本用例创建的库 ledger")
    if name == "ledger" and _deliveries_have_rows(name):
        raise RuntimeError("拒绝删除含 deliveries 数据的库 ledger")
    admin = _admin()
    try:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        admin.dispose()
        forget_created(name)


def _create_database(name: str) -> None:
    assert_isolated_database()
    if _exists(name):
        if name == "ledger":
            pytest.fail("目标实例已有库 ledger，拒绝 CREATE/DROP，以免碰到交付台账")
        _drop_database(name)
    admin = _admin()
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        remember_created(name)
    finally:
        admin.dispose()


def _public_tables() -> set[str]:
    from app.db import engine

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars()
        return set(rows)


def _drop_app_tables() -> None:
    from app.db import engine

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS assets, spaces, schema_migration CASCADE"))


def test_product_code_refuses_before_create(database_ready, capsys, monkeypatch):
    monkeypatch.setenv("PRODUCT_CODE", "other")
    _drop_app_tables()
    try:
        with pytest.raises(SystemExit) as caught:
            boot()
        assert caught.value.code not in (0, None)
        assert "PRODUCT_CODE 必须是 asset-ledger" in capsys.readouterr().err
        assert "assets" not in _public_tables()
        assert "schema_migration" not in _public_tables()
    finally:
        monkeypatch.setenv("PRODUCT_CODE", "asset-ledger")
        boot()


def test_ledger_database_blocks_startup(database_ready, capsys):
    _create_database("ledger")
    _drop_app_tables()
    try:
        with pytest.raises(SystemExit) as caught:
            boot()
        assert caught.value.code not in (0, None)
        assert "数据库卷与客户交付台账冲突" in capsys.readouterr().err
        assert "assets" not in _public_tables()
        assert "schema_migration" not in _public_tables()
    finally:
        _drop_database("ledger")
        boot()


def test_deliveries_in_another_database_blocks_startup(database_ready, capsys):
    _create_database("side_asset_probe")
    side = create_engine(
        make_url(os.environ["DATABASE_URL"]).set(database="side_asset_probe"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    with side.connect() as conn:
        conn.execute(text("CREATE TABLE deliveries (id integer)"))
    side.dispose()
    _drop_app_tables()
    try:
        with pytest.raises(SystemExit) as caught:
            boot()
        assert caught.value.code not in (0, None)
        assert "数据库卷与客户交付台账冲突" in capsys.readouterr().err
        assert "assets" not in _public_tables()
        names = _public_tables()
        assert "schema_migration" not in names
    finally:
        _drop_database("side_asset_probe")
        boot()


def test_cannot_check_volume_owner(database_ready, capsys, monkeypatch):
    monkeypatch.setattr(
        "app.cluster.database_url",
        lambda: "postgresql+psycopg://asset_ledger:asset_ledger@127.0.0.1:1/asset_ledger_test",
    )
    with pytest.raises(SystemExit) as caught:
        assert_cluster_exclusive()
    assert caught.value.code not in (0, None)
    assert "无法检查数据库卷归属" in capsys.readouterr().err


def test_schema_migration_recorded(database_ready):
    boot()
    from app.db import engine

    with engine.connect() as conn:
        versions = list(conn.execute(text("SELECT version FROM schema_migration")).scalars())
    assert "0.1.0" in versions
