import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_bash(script: str, env=None):
    merged = os.environ.copy()
    merged.pop("COMPOSE_PROJECT_NAME", None)
    if env:
        merged.update(env)
    return subprocess.run(["bash", "-c", script], cwd=ROOT, env=merged, text=True, capture_output=True)


def test_shell_syntax():
    for path in (ROOT / "deploy").glob("*.sh"):
        result = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr


def test_version_and_dependency_pins():
    assert (ROOT / "VERSION").read_text().strip() == "0.1.0"
    project = (ROOT / "pyproject.toml").read_text()
    for pin in (
        'version = "0.1.0"',
        "fastapi==0.115.6",
        "uvicorn==0.32.1",
        "jinja2==3.1.4",
        "sqlalchemy==2.0.36",
        "psycopg[binary]>=3.2.4",
        "python-multipart==0.0.17",
        "itsdangerous==2.2.0",
        "openpyxl==3.1.5",
        "et-xmlfile==2.0.0",
    ):
        assert pin in project
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "pip install --no-cache-dir --no-index --find-links=/wheels ." in dockerfile
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile
    assert "pypi" not in dockerfile.lower()
    migrate = (ROOT / "app" / "migrate.py").read_text().upper()
    for banned in ("DROP ", "TRUNCATE", "DELETE FROM"):
        assert banned not in migrate


def test_vendor_wheels_are_linux_amd64():
    wheels = list((ROOT / "vendor" / "wheels").glob("*.whl"))
    names = [path.name for path in wheels]
    assert names, "vendor/wheels 里没有 wheel，离线镜像构建会失败"
    assert not any("macosx" in name or "win_" in name for name in names)
    assert any(name.startswith("openpyxl-3.1.5-") for name in names)
    assert any("psycopg_binary" in name and "manylinux" in name and "x86_64" in name for name in names)


def test_spec_requires_postgres_command():
    spec = (ROOT / "功能说明.md").read_text()
    assert 'command` 是 `["postgres"]`' in spec
    assert 'command` 是 `["postgres"]`' in (ROOT / "发布构建标准.md").read_text()
    assert 'command` 是 `["postgres"]`' in (ROOT / "部署说明.md").read_text()
    assert 'command` 是 `["postgres"]`' in (ROOT / "AGENT提示词.md").read_text()


def test_compose_contract():
    text = (ROOT / "docker-compose.yml").read_text()
    assert text.startswith("name: asset-ledger\n")
    assert "name: delivery_ledger_pgdata" in text
    assert text.count("pull_policy: never") == 2
    assert "/pg-guard.sh" in text
    assert 'command: ["postgres"]' in text
    assert "asset-ledger:${APP_VERSION:-0.1.0}" in text
    assert "APP_VERSION: ${APP_VERSION:-0.1.0}" in text
    assert "${APP_PORT:-8010}:8000" in text
    postgres, app = text.split("  app:", 1)
    assert "ports:" not in postgres
    assert "condition: service_healthy" in app
    example = (ROOT / ".env.example").read_text()
    for key in (
        "DATABASE_URL=postgresql+psycopg://asset_ledger:PASSWORD@postgres:5432/asset_ledger",
        "POSTGRES_USER=asset_ledger",
        "POSTGRES_PASSWORD=PASSWORD",
        "POSTGRES_DB=asset_ledger",
        "APP_PORT=8010",
        "PRODUCT_CODE=asset-ledger",
        "TZ=Asia/Shanghai",
    ):
        assert key in example
    joined = "\n".join(path.read_text() for path in (ROOT / "deploy").glob("*.sh"))
    assert "down -v" not in joined
    assert "docker volume rm" not in joined


def test_start_scripts_only_call_shared_guard():
    lib = (ROOT / "deploy" / "lib.sh").read_text()
    assert "assert_volume_exclusive()" in lib
    assert "COMPOSE_PROJECT_NAME 必须是 asset-ledger" in lib
    assert "禁止与客户交付台账同机部署" in lib
    assert "卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载" in lib
    assert 'docker compose -p asset-ledger --project-directory "$INSTALL_DIR"' in lib
    assert "POSTGRES_DB=asset_ledger" in lib
    for name in ("install.sh", "upgrade.sh", "up.sh"):
        script = (ROOT / "deploy" / name).read_text()
        assert "assert_volume_exclusive" in script
        assert "assert_volume_exclusive()" not in script
        assert 'source "$(cd "$(dirname "$0")" && pwd)/lib.sh"' in script or "source " in script
    assert "已有安装，请使用 upgrade.sh" in (ROOT / "deploy" / "install.sh").read_text()
    upgrade = (ROOT / "deploy" / "upgrade.sh").read_text()
    assert "ALLOW_DOWNGRADE" in upgrade
    assert upgrade.index("assert_volume_exclusive") < upgrade.index("backup_to")
    assert upgrade.index("backup_to") < upgrade.index("replace_code")
    restore = (ROOT / "deploy" / "restore.sh").read_text()
    assert "DROP DATABASE asset_ledger" in restore
    assert "CREATE DATABASE asset_ledger OWNER asset_ledger" in restore
    assert "数据库卷与客户交付台账冲突" in restore
    assert "to_regclass('public.deliveries')" in restore
    backup = (ROOT / "deploy" / "lib.sh").read_text()
    assert 'pg_dump -U "$POSTGRES_USER" -d asset_ledger --no-owner --no-acl' in backup
    assert "files.tar.gz" not in backup


def _docker_mock(tmp_path: Path) -> Path:
    path = tmp_path / "docker"
    path.write_text(
        """#!/usr/bin/env python3
import os, sys
args = sys.argv[1:]
log = os.environ.get("DOCKER_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(" ".join(args) + "\\n")
mode = os.environ.get("FAKE_DOCKER", "clean")
if args == ["info"] or args[:2] == ["compose", "version"]:
    raise SystemExit(0)
if args[:2] == ["ps", "-aq"]:
    if mode in {"delivery-image", "delivery-project", "foreign-mount", "sha-only", "own-mount"}:
        print("c1")
    raise SystemExit(0)
if args[:2] == ["volume", "inspect"]:
    if mode in {"no-volume"}:
        raise SystemExit(1)
    if any(arg.startswith("--format") for arg in args):
        print(os.environ.get("VOLUME_LABEL", ""))
    raise SystemExit(0)
if args[:1] == ["inspect"] and "-f" in args:
    fmt = args[args.index("-f") + 1]
    project = os.environ.get("FAKE_PROJECT", "")
    mounts = os.environ.get("FAKE_MOUNTS", "")
    image = os.environ.get("FAKE_IMAGE", "postgres:16")
    image_id = os.environ.get("FAKE_IMAGE_ID", "sha256:abc")
    if "Mounts" in fmt:
        if mounts:
            print(mounts)
    elif ".Config.Image" in fmt:
        print(image)
    elif fmt.strip() == "{{.Image}}":
        print(image_id)
    elif "com.docker.compose.project" in fmt:
        print(project)
    raise SystemExit(0)
if args[:2] == ["image", "inspect"]:
    print(os.environ.get("FAKE_REFS", ""))
    raise SystemExit(0)
if args[:1] == ["compose"]:
    raise SystemExit(0)
raise SystemExit(0)
"""
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


def test_assert_volume_cases(tmp_path):
    mock = _docker_mock(tmp_path)
    log = tmp_path / "docker.log"
    base = {"PATH": f"{tmp_path}:{os.environ['PATH']}", "DOCKER_LOG": str(log), "INSTALL_DIR": str(tmp_path)}
    script = f'source "{ROOT}/deploy/lib.sh"; assert_volume_exclusive'

    log.write_text("")
    other = run_bash(script, {**base, "COMPOSE_PROJECT_NAME": "other"})
    assert other.returncode != 0
    assert "COMPOSE_PROJECT_NAME 必须是 asset-ledger" in other.stderr
    assert log.read_text() == ""

    cases = [
        ("no-volume", {}, 0, ""),
        ("clean", {"VOLUME_LABEL": "asset-ledger"}, 0, ""),
        (
            "volume-foreign",
            {"VOLUME_LABEL": ""},
            1,
            "卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载",
        ),
        (
            "delivery-image",
            {"FAKE_PROJECT": "other", "FAKE_IMAGE": "delivery-ledger:1.0", "FAKE_REFS": "delivery-ledger:1.0", "VOLUME_LABEL": "asset-ledger"},
            1,
            "禁止与客户交付台账同机部署",
        ),
        (
            "delivery-project",
            {"FAKE_PROJECT": "delivery-ledger", "FAKE_IMAGE": "postgres:16", "VOLUME_LABEL": "asset-ledger"},
            1,
            "禁止与客户交付台账同机部署",
        ),
        (
            "foreign-mount",
            {
                "FAKE_PROJECT": "other",
                "FAKE_MOUNTS": "delivery_ledger_pgdata",
                "FAKE_IMAGE": "postgres:16",
                "VOLUME_LABEL": "asset-ledger",
            },
            1,
            "禁止与客户交付台账同机部署",
        ),
        (
            "sha-only",
            {
                "FAKE_PROJECT": "asset-ledger",
                "FAKE_IMAGE": "sha256:deadbeef",
                "FAKE_IMAGE_ID": "sha256:deadbeef",
                "FAKE_REFS": "sha256:deadbeef",
                "VOLUME_LABEL": "asset-ledger",
            },
            0,
            "",
        ),
        (
            "own-mount",
            {
                "FAKE_PROJECT": "asset-ledger",
                "FAKE_MOUNTS": "delivery_ledger_pgdata",
                "FAKE_IMAGE": "asset-ledger:0.1.0",
                "FAKE_REFS": "asset-ledger:0.1.0",
                "VOLUME_LABEL": "asset-ledger",
            },
            0,
            "",
        ),
    ]
    for mode, extra, code, message in cases:
        env = {**base, "FAKE_DOCKER": mode, **extra}
        result = run_bash(script, env)
        assert result.returncode == code, (mode, result.stderr, result.stdout)
        if message:
            assert message in result.stderr


def test_install_and_up_stop_before_compose(tmp_path):
    _docker_mock(tmp_path)
    log = tmp_path / "docker.log"
    log.write_text("")
    dest = tmp_path / "opt"
    dest.mkdir()
    env = {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DOCKER_LOG": str(log),
        "FAKE_DOCKER": "volume-foreign",
        "VOLUME_LABEL": "",
    }
    installed = run_bash(f'"{ROOT}/deploy/install.sh" "{dest}"', env)
    assert installed.returncode != 0
    assert "卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载" in installed.stderr
    assert "up" not in log.read_text()
    assert not (dest / "VERSION").exists()

    log.write_text("")
    env["COMPOSE_PROJECT_NAME"] = "other"
    started = run_bash(f'"{ROOT}/deploy/up.sh"', env)
    assert started.returncode != 0
    assert "COMPOSE_PROJECT_NAME 必须是 asset-ledger" in started.stderr
    assert "up" not in log.read_text()

    marked = tmp_path / "already"
    marked.mkdir()
    (marked / "VERSION").write_text("0.0.1\n")
    again = run_bash(f'"{ROOT}/deploy/install.sh" "{marked}"')
    assert again.returncode != 0
    assert "已有安装，请使用 upgrade.sh" in again.stderr
    assert (marked / "VERSION").read_text() == "0.0.1\n"


def test_write_env_and_replace_keeps_secrets(tmp_path):
    dest = tmp_path / "install"
    fresh = tmp_path / "fresh"
    dest.mkdir()
    fresh.mkdir()
    (dest / ".env").write_text("POSTGRES_PASSWORD=keep-me\n")
    (dest / "backups").mkdir()
    (dest / "backups" / "keep.txt").write_text("stay")
    (dest / "VERSION").write_text("0.0.1\n")
    script = f'''
source "{ROOT}/deploy/lib.sh"
write_env "{fresh}"
replace_code "{dest}"
'''
    result = run_bash(script)
    assert result.returncode == 0, result.stderr
    fresh_env = (fresh / ".env").read_text()
    assert "PRODUCT_CODE=asset-ledger" in fresh_env
    assert "APP_PORT=8010" in fresh_env
    assert "PASSWORD" not in fresh_env.split("POSTGRES_PASSWORD=", 1)[1].splitlines()[0]
    mode = oct((tmp_path / "fresh" / ".env").stat().st_mode & 0o777)
    assert mode == "0o600"
    assert "keep-me" in (dest / ".env").read_text()
    assert (dest / "backups" / "keep.txt").read_text() == "stay"
    assert (dest / "VERSION").read_text().strip() == "0.1.0"


def _guard(tmp_path: Path, data: Path, entry: Path) -> subprocess.CompletedProcess:
    script = (ROOT / "deploy" / "pg-guard.sh").read_text().replace("/usr/local/bin/docker-entrypoint.sh", str(entry))
    copied = tmp_path / "pg-guard.sh"
    copied.write_text(script)
    copied.chmod(0o755)
    return subprocess.run(["bash", str(copied)], cwd=tmp_path, text=True, capture_output=True, env={**os.environ, "PGDATA": str(data)})


def test_pg_guard_refuses_unmarked_data(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "PG_VERSION").write_text("16\n")
    (data / "keep").write_text("unchanged")
    entry = tmp_path / "entry.sh"
    entry.write_text("#!/bin/bash\necho called > \"$PGDATA/called\"\n")
    entry.chmod(0o755)
    result = _guard(tmp_path, data, entry)
    assert result.returncode != 0
    assert "不属于本产品" in result.stderr
    assert not (data / "called").exists()
    assert not (data / "asset_ledger.owner").exists()
    assert (data / "keep").read_text() == "unchanged"


def test_pg_guard_accepts_legal_marker_and_init(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "PG_VERSION").write_text("16\n")
    (data / "asset_ledger.owner").write_text("asset-ledger\n")
    entry = tmp_path / "entry.sh"
    entry.write_text("#!/bin/bash\necho started\n")
    entry.chmod(0o755)
    result = _guard(tmp_path, data, entry)
    assert result.returncode == 0, result.stderr
    assert "started" in result.stdout

    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "PG_VERSION").write_text("16")
    (bare / "asset_ledger.owner").write_bytes(b"asset-ledger")
    result = _guard(tmp_path, bare, entry)
    assert result.returncode == 0

    illegal = tmp_path / "illegal"
    illegal.mkdir()
    (illegal / "PG_VERSION").write_text("16\n")
    (illegal / "asset_ledger.owner").write_bytes(b"asset-ledger\n\n")
    result = _guard(tmp_path, illegal, entry)
    assert result.returncode != 0
    assert "不属于本产品" in result.stderr

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    init_entry = tmp_path / "init.sh"
    init_entry.write_text(
        """#!/bin/bash
echo 16 > "$PGDATA/PG_VERSION"
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if [ -f "$PGDATA/asset_ledger.owner" ]; then
    exit 0
  fi
  sleep 0.05
done
exit 2
"""
    )
    init_entry.chmod(0o755)
    result = _guard(tmp_path, fresh, init_entry)
    assert result.returncode == 0, result.stderr
    marker = (fresh / "asset_ledger.owner").read_bytes()
    if marker.endswith(b"\n"):
        marker = marker[:-1]
    assert marker == b"asset-ledger"

    failed = tmp_path / "failed"
    failed.mkdir()
    fail_entry = tmp_path / "fail.sh"
    fail_entry.write_text("#!/bin/bash\nexit 7\n")
    fail_entry.chmod(0o755)
    result = _guard(tmp_path, failed, fail_entry)
    assert result.returncode == 7
    assert "不属于本产品" not in result.stderr
    assert not (failed / "PG_VERSION").exists()
    assert not (failed / "asset_ledger.owner").exists()
