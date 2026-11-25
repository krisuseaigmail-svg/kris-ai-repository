#!/bin/bash
# 首次安装（离线镜像）。用法: ./deploy/install.sh /opt/asset-ledger
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

INSTALL_DIR=${1:-/opt/asset-ledger}
if [ -d "$INSTALL_DIR" ]; then
  existing=$(CDPATH= cd -- "$INSTALL_DIR" && pwd)
  [ "$existing" = "$PKG_ROOT" ] && die "安装目录不能是解压出来的这份目录。请指定另一个目录，例如 /opt/asset-ledger"
fi
if [ -f "$INSTALL_DIR/VERSION" ]; then
  echo "已有安装，请使用 upgrade.sh" >&2
  exit 1
fi

require_docker
assert_volume_exclusive

mkdir -p "$INSTALL_DIR"
copy_release "$INSTALL_DIR"
write_env "$INSTALL_DIR"
load_env

echo "正在加载离线镜像并启动 $(read_version "$INSTALL_DIR")"
start_stack
wait_health
echo "安装完成。配置文件: $INSTALL_DIR/.env"
echo "浏览器打开: http://<服务器地址>:$(app_port)/"
