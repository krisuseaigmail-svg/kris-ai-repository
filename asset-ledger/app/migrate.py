from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

SHANGHAI = ZoneInfo("Asia/Shanghai")

# 只在列表末尾追加。已经执行过的版本不再执行。
# 0.1.0：初始表 spaces、assets，由启动时创建。
MIGRATIONS: list[tuple[str, tuple[str, ...]]] = [
    ("0.1.0", ()),
]


def apply_migrations(bound_engine) -> None:
    with bound_engine.begin() as conn:
        done = set(conn.execute(text("SELECT version FROM schema_migration")).scalars())
        for version, statements in MIGRATIONS:
            if version in done:
                continue
            for statement in statements:
                conn.execute(text(statement))
            conn.execute(
                text("INSERT INTO schema_migration (version, applied_at) VALUES (:version, :applied_at)"),
                {"version": version, "applied_at": datetime.now(SHANGHAI)},
            )
