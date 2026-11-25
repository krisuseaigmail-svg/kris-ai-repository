#!/bin/bash
# 用法: ./deploy/backup.sh /opt/asset-ledger
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
require_docker
INSTALL_DIR=${1:-$PKG_ROOT}
INSTALL_DIR=$(CDPATH= cd -- "$INSTALL_DIR" && pwd)
load_env
backup_dir=$(backup_to)
echo "备份完成: $backup_dir"
