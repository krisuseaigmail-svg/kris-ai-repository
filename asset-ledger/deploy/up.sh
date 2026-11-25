#!/bin/bash
# 按 VERSION 加载离线镜像并启动。用法: ./deploy/up.sh
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
require_docker
INSTALL_DIR=$PKG_ROOT
assert_volume_exclusive
load_env
start_stack
wait_health
