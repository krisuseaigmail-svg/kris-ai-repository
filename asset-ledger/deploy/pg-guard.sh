#!/bin/bash
# postgres 入口包装。已有 PG_VERSION 但没有合法 asset_ledger.owner 时拒绝开库。
set -euo pipefail

DATA_DIR="${PGDATA:-/var/lib/postgresql/data}"
MARKER="$DATA_DIR/asset_ledger.owner"
ENTRYPOINT="/usr/local/bin/docker-entrypoint.sh"

marker_ok() {
  [ -f "$MARKER" ] || return 1
  local expected with_nl
  expected=$(mktemp)
  with_nl=$(mktemp)
  printf '%s' 'asset-ledger' > "$expected"
  printf '%s\n' 'asset-ledger' > "$with_nl"
  if cmp -s "$MARKER" "$expected" || cmp -s "$MARKER" "$with_nl"; then
    rm -f "$expected" "$with_nl"
    return 0
  fi
  rm -f "$expected" "$with_nl"
  return 1
}

write_marker() {
  printf '%s\n' 'asset-ledger' > "$MARKER"
  sync
}

if [ ! -f "$DATA_DIR/PG_VERSION" ]; then
  child=0
  forward() {
    sig=$1
    if [ "$child" -ne 0 ]; then
      kill "-$sig" "$child" 2>/dev/null || true
      wait "$child" 2>/dev/null || true
    fi
  }
  trap 'forward TERM; exit 143' TERM
  trap 'forward INT; exit 130' INT
  "$ENTRYPOINT" "$@" &
  child=$!
  while kill -0 "$child" 2>/dev/null; do
    if [ -f "$DATA_DIR/PG_VERSION" ] && [ ! -f "$MARKER" ]; then
      write_marker
    fi
    sleep 0.05
  done
  set +e
  wait "$child"
  status=$?
  set -e
  if [ -f "$DATA_DIR/PG_VERSION" ] && [ ! -f "$MARKER" ]; then
    write_marker
  fi
  exit "$status"
fi

if marker_ok; then
  exec "$ENTRYPOINT" "$@"
fi

echo "卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载" >&2
exit 1
