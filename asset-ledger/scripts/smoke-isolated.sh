#!/bin/bash
# 开发机冒烟。用覆盖文件把卷名改成临时名，再调用官方 install.sh / upgrade.sh。
# 不改 docker-compose.yml 里的生产卷名，也不删除 delivery_ledger_pgdata。
# 用法: ./scripts/smoke-isolated.sh <发布包或仓库根> <安装目录>
# 同版本升级演练: SMOKE_WITH_UPGRADE=1 ./scripts/smoke-isolated.sh <根> <安装目录>
set -euo pipefail

PKG=${1:-}
DEST=${2:-}
[ -n "$PKG" ] && [ -n "$DEST" ] || {
  echo "用法: $0 <发布包根目录> <安装目录>" >&2
  exit 1
}
PKG=$(CDPATH= cd -- "$PKG" && pwd)
SMOKE_VOLUME_NAME=${SMOKE_VOLUME_NAME:-asset_ledger_smoke_pgdata}
export SMOKE_VOLUME_NAME

if [ "$SMOKE_VOLUME_NAME" = "delivery_ledger_pgdata" ]; then
  echo "冒烟卷名不能是生产卷 delivery_ledger_pgdata" >&2
  exit 1
fi
if [ ! -f "$PKG/docker-compose.yml" ] || [ ! -f "$PKG/scripts/compose.smoke-volume.yml" ]; then
  echo "目录里没有 docker-compose.yml 或 scripts/compose.smoke-volume.yml" >&2
  exit 1
fi
if grep -q 'name: delivery_ledger_pgdata' "$PKG/scripts/compose.smoke-volume.yml"; then
  echo "覆盖文件不能把卷名写成生产卷" >&2
  exit 1
fi

export COMPOSE_FILE="$PKG/docker-compose.yml:$PKG/scripts/compose.smoke-volume.yml"
echo "冒烟卷: $SMOKE_VOLUME_NAME"
echo "安装到: $DEST"
"$PKG/deploy/install.sh" "$DEST"

if [ "${SMOKE_WITH_UPGRADE:-}" = "1" ]; then
  port=$(grep '^APP_PORT=' "$DEST/.env" | cut -d= -f2-)
  port=${port:-8010}
  url="http://127.0.0.1:${port}/spaces"
  i=0
  while [ "$i" -lt 40 ]; do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port}/healthz" || true)
    if [ "$code" = "200" ]; then
      break
    fi
    i=$((i + 1))
    sleep 2
  done
  curl -fsS -D - -o /dev/null -X POST "$url" \
    --data-urlencode 'name=冒烟机房' \
    --data-urlencode 'kind=room' \
    --data-urlencode 'parent_id=' \
    --data-urlencode 'rack_height=' \
    --data-urlencode 'note='
  cp "$DEST/.env" /tmp/asset-ledger-smoke-env.before
  "$PKG/deploy/upgrade.sh" "$DEST"
  echo "升级后请核对: 页面仍有「冒烟机房」，.env 密码与升级前一致，标记文件仍是 asset-ledger。"
fi
