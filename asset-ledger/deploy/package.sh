#!/bin/bash
# 在开发机上打离线发布包（含真正的 linux/amd64 单架构镜像）。用法: ./deploy/package.sh
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

require_docker
version=$(read_version "$PKG_ROOT")
platform="${PACKAGE_PLATFORM:-linux/amd64}"
app_image="asset-ledger:${version}"
pg_image="postgres:16"
base_mirror="${PACKAGE_BASE_MIRROR:-docker.m.daocloud.io/library}"
out="$PKG_ROOT/dist/asset-ledger-${version}.tar.gz"
stage=$(mktemp -d)
cleanup() { rm -rf "$stage"; }
trap cleanup EXIT

echo "目标平台: $platform"

wheels_dir="$PKG_ROOT/vendor/wheels"
mkdir -p "$wheels_dir"
if ! ls "$wheels_dir"/*.whl >/dev/null 2>&1; then
  echo "下载 linux/amd64 二进制 wheel（含 SQLAlchemy、pydantic-core、MarkupSafe）"
  python3 -m pip download \
    -d "$wheels_dir" \
    -i "${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}" \
    --python-version 312 \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --abi cp312 \
    --only-binary=:all: \
    "psycopg-binary==3.2.13" \
    "greenlet" \
    "sqlalchemy==2.0.36" \
    "pydantic-core==2.46.5" \
    "markupsafe==3.0.4"
  echo "下载纯 Python wheel（不带 --platform，避免滤掉 py3-none-any；--no-deps 以免再拉到本机架构包）"
  python3 -m pip download \
    -d "$wheels_dir" \
    -i "${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}" \
    --no-deps \
    "fastapi==0.115.6" \
    "uvicorn==0.32.1" \
    "jinja2==3.1.4" \
    "psycopg==3.2.13" \
    "python-multipart==0.0.17" \
    "itsdangerous==2.2.0" \
    "openpyxl==3.1.5" \
    "et-xmlfile==2.0.0" \
    "starlette==0.41.3" \
    "pydantic==2.13.5" \
    "click==8.1.8" \
    "h11==0.16.0" \
    "annotated-types==0.7.0" \
    "anyio==4.12.1" \
    "exceptiongroup==1.3.1" \
    "idna==3.20" \
    "typing-extensions==4.16.0" \
    "typing-inspection==0.4.2" \
    "setuptools>=68" \
    "wheel" \
    "pip" \
    "packaging"
fi

flatten_amd64() {
  src=$1
  dest=$2
  echo "压成单架构 amd64: $src -> $dest"
  cid=$(docker create --platform linux/amd64 "$src")
  docker commit "$cid" "$dest" >/dev/null
  docker rm "$cid" >/dev/null
}

assert_amd64() {
  img=$1
  arch=$(docker image inspect "$img" --format '{{.Architecture}}')
  [ "$arch" = "amd64" ] || die "$img 的 Architecture=$arch，需要 amd64（请检查 flatten 步骤）"
  machine=$(docker run --rm --platform linux/amd64 "$img" uname -m)
  [ "$machine" = "x86_64" ] || die "$img 运行 uname=$machine，需要 x86_64"
  echo "校验通过: $img (amd64 / $machine)"
}

echo "准备基础镜像 $base_mirror/python:3.12-slim"
docker pull --platform "$platform" "$base_mirror/python:3.12-slim"
flatten_amd64 "$base_mirror/python:3.12-slim" python:3.12-slim
assert_amd64 python:3.12-slim

echo "构建应用镜像 $app_image"
docker buildx build \
  --platform "$platform" \
  --provenance=false \
  --sbom=false \
  -t "${app_image}-build" \
  --load \
  --pull=false \
  "$PKG_ROOT"
flatten_amd64 "${app_image}-build" "$app_image"
assert_amd64 "$app_image"

echo "准备数据库镜像 $base_mirror/postgres:16"
docker pull --platform "$platform" "$base_mirror/postgres:16"
flatten_amd64 "$base_mirror/postgres:16" "$pg_image"
assert_amd64 "$pg_image"

mkdir -p "$stage/asset-ledger/images" "$PKG_ROOT/dist"
echo "导出离线镜像（可能较大）"
docker save "$app_image" "$pg_image" | gzip -1 > "$stage/asset-ledger/images/asset-ledger-images-amd64.tar.gz"

tar \
  --exclude dist \
  --exclude .venv \
  --exclude .pytest_cache \
  --exclude __pycache__ \
  --exclude .env \
  --exclude backups \
  --exclude .git \
  --exclude images \
  --exclude .DS_Store \
  --exclude '*/.DS_Store' \
  -C "$PKG_ROOT" -cf - . | tar -C "$stage/asset-ledger" -xf -
chmod 755 "$stage/asset-ledger"/deploy/*.sh

cat > "$stage/asset-ledger/images/README.txt" <<EOF
离线镜像（强制单架构 ${platform}）
- ${app_image}
- ${pg_image}
若服务器报 exec format error，说明装了错误架构镜像；请换用本包重新 load。
EOF

tar -C "$stage" -czf "$out" asset-ledger
echo "$out"
ls -lh "$out"
