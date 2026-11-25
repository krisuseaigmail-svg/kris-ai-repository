#!/bin/bash
# 从一次备份恢复数据库 asset_ledger。用法: ./deploy/restore.sh /opt/asset-ledger /opt/asset-ledger/backups/20261111180000
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
require_docker

INSTALL_DIR=${1:-}
BACKUP_DIR=${2:-}
[ -n "$INSTALL_DIR" ] && [ -n "$BACKUP_DIR" ] || die "用法: $0 <安装目录> <备份目录>"
INSTALL_DIR=$(CDPATH= cd -- "$INSTALL_DIR" && pwd)
[ -f "$BACKUP_DIR/db.sql" ] || die "备份里没有 db.sql"
[ -f "$BACKUP_DIR/VERSION" ] || die "备份里没有 VERSION"

assert_volume_exclusive
load_env
postgres_healthy || die "本产品的 postgres 尚未就绪"

dbs=$(compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -Atc "SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate")
printf '%s\n' "$dbs" | while IFS= read -r db; do
  [ -n "$db" ] || continue
  if [ "$db" = "ledger" ]; then
    echo "数据库卷与客户交付台账冲突" >&2
    exit 1
  fi
done
printf '%s\n' "$dbs" | while IFS= read -r db; do
  [ -n "$db" ] || continue
  hit=$(compose exec -T postgres psql -U "$POSTGRES_USER" -d "$db" -Atc "SELECT to_regclass('public.deliveries') IS NOT NULL")
  hit=$(printf '%s' "$hit" | tr -d '[:space:]')
  if [ "$hit" = "t" ]; then
    echo "数据库卷与客户交付台账冲突" >&2
    exit 1
  fi
done

compose stop app || true
compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'asset_ledger' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE asset_ledger;" \
  -c "CREATE DATABASE asset_ledger OWNER asset_ledger;"
compose exec -T postgres psql -U "$POSTGRES_USER" -d asset_ledger -v ON_ERROR_STOP=1 < "$BACKUP_DIR/db.sql"
export APP_VERSION
APP_VERSION=$(read_version "$INSTALL_DIR")
compose up -d --pull never
wait_health
echo "已恢复 $BACKUP_DIR"
