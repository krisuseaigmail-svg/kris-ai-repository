#!/bin/bash
# 用新版本压缩包升级已安装目录。保留 .env、backups、卷和 asset_ledger.owner。
# 用法: ./deploy/upgrade.sh /opt/asset-ledger
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
require_docker

INSTALL_DIR=${1:-}
[ -n "$INSTALL_DIR" ] || die "用法: $0 /opt/asset-ledger"
INSTALL_DIR=$(CDPATH= cd -- "$INSTALL_DIR" && pwd)
[ "$INSTALL_DIR" = "$PKG_ROOT" ] && die "请先把新版本解压到别的目录，再执行该目录里的 deploy/upgrade.sh <已安装目录>"
[ -f "$INSTALL_DIR/VERSION" ] || die "$INSTALL_DIR 不是已安装目录。首次安装用 deploy/install.sh"
[ -f "$INSTALL_DIR/.env" ] || die "$INSTALL_DIR 缺少 .env，不能升级"

old=$(read_version "$INSTALL_DIR")
new=$(read_version "$PKG_ROOT")
if [ "$new" != "$old" ]; then
  first=$(printf '%s\n%s\n' "$old" "$new" | sort -V | head -n 1)
  if [ "$first" = "$new" ] && [ "${ALLOW_DOWNGRADE:-}" != "1" ]; then
    die "新版本 $new 低于已安装 $old。确认要回退时，先恢复对应备份，再执行 ALLOW_DOWNGRADE=1 $0 $INSTALL_DIR"
  fi
fi

assert_volume_exclusive

load_env
echo "升级前备份 $old"
if ! backup_dir=$(backup_to); then
  die "备份失败，未替换程序"
fi
echo "备份目录: $backup_dir"

echo "替换程序与镜像，保留 .env、backups 和卷"
replace_code "$INSTALL_DIR"
echo "启动 $new"
if ! start_stack; then
  echo "容器启动失败。备份仍在 $backup_dir" >&2
  exit 1
fi
if ! wait_health; then
  echo "新版本没有通过健康检查。数据备份在 $backup_dir" >&2
  exit 1
fi
echo "升级完成: $old -> $(read_version "$INSTALL_DIR")"
echo "这一版的备份: $backup_dir"
