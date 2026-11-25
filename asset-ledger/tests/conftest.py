import os
import time

from tests.isolation import assert_isolated_database, database_url

os.environ["DATABASE_URL"] = database_url()
assert_isolated_database()
os.environ.setdefault("PRODUCT_CODE", "asset-ledger")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.db import engine
from app.main import app, boot
from app.services import reset_data


def ensure_database() -> bool:
    assert_isolated_database()
    url = make_url(os.environ["DATABASE_URL"])
    last_error = None
    for _ in range(30):
        admin = None
        try:
            admin = create_engine(
                url.set(database="postgres"),
                isolation_level="AUTOCOMMIT",
                poolclass=NullPool,
                connect_args={"connect_timeout": 2},
            )
            with admin.connect() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                ).scalar()
                if not exists:
                    conn.execute(text(f'CREATE DATABASE "{url.database}"'))
            return True
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
        finally:
            if admin is not None:
                admin.dispose()
    print(f"独立测试库不可用: {last_error}")
    return False


@pytest.fixture(scope="session")
def database_ready():
    if not ensure_database():
        pytest.fail(
            "独立测试库不可用。默认连接 127.0.0.1:5433/asset_ledger_test，"
            "不要改连端口 5432 上的客户交付台账。"
        )
    os.environ["PRODUCT_CODE"] = "asset-ledger"
    boot()
    return True


@pytest.fixture()
def client(database_ready):
    boot()
    with TestClient(app) as test_client:
        reset_data()
        yield test_client


@pytest.fixture()
def db_session(database_ready):
    boot()
    reset_data()
    yield
    reset_data()
