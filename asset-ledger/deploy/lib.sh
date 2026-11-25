# 被 install.sh、upgrade.sh、up.sh source。不要直接执行。

_LIB_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PKG_ROOT=$(CDPATH= cd -- "$_LIB_DIR/.." && pwd)

die() {
  echo "错误: $*" >&2
  exit 1
}

require_docker() {
  command -v docker >/dev/null 2>&1 || die "服务器上没有 docker"
  docker info >/dev/null 2>&1 || die "当前用户不能访问 Docker。请加入 docker 组，或使用 root"
  docker compose version >/dev/null 2>&1 || die "没有 Docker Compose。请安装 docker compose 插件"
}

compose() {
  docker compose -p asset-ledger --project-directory "$INSTALL_DIR" "$@"
}

read_version() {
  tr -d '[:space:]' < "$1/VERSION"
}

load_env() {
  [ -f "$INSTALL_DIR/.env" ] || die "缺少 $INSTALL_DIR/.env"
  set -a
  # shellcheck disable=SC1091
  . "$INSTALL_DIR/.env"
  set +a
  [ -n "${POSTGRES_USER:-}" ] || die ".env 里没有 POSTGRES_USER"
  [ -n "${POSTGRES_DB:-}" ] || die ".env 里没有 POSTGRES_DB"
}

app_port() {
  printf '%s' "${APP_PORT:-8010}"
}

postgres_healthy() {
  cid=$(compose ps -q postgres 2>/dev/null || true)
  [ -n "$cid" ] || return 1
  status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$cid" 2>/dev/null || true)
  [ "$status" = "healthy" ]
}

wait_health() {
  port=$(app_port)
  url="http://127.0.0.1:${port}/healthz"
  i=0
  while [ "$i" -lt 40 ]; do
    body=$(curl -fsS "$url" 2>/dev/null || true)
    trimmed=$(printf '%s' "$body" | tr -d '[:space:]')
    if [ "$trimmed" = "ok" ]; then
      echo "应用已就绪: $url"
      printf '%s\n' "$body"
      return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  echo "应用没有在预期时间内就绪。最近日志:" >&2
  compose logs --tail 80 app >&2 || true
  return 1
}

copy_release() {
  dest=$1
  mkdir -p "$dest/backups"
  tar \
    --exclude dist \
    --exclude .venv \
    --exclude .pytest_cache \
    --exclude __pycache__ \
    --exclude .env \
    --exclude backups \
    --exclude .git \
    --exclude .DS_Store \
    --exclude '*/.DS_Store' \
    -C "$PKG_ROOT" -cf - . | tar -C "$dest" -xf -
}

load_offline_images() {
  root=${1:-$PKG_ROOT}
  dir="$root/images"
  [ -d "$dir" ] || die "发布包缺少 images/。请使用带离线镜像的压缩包（./deploy/package.sh 打出）"
  found=0
  for f in "$dir"/*.tar.gz "$dir"/*.tar; do
    [ -e "$f" ] || continue
    found=1
    echo "加载镜像: $(basename "$f")"
    case "$f" in
      *.tar.gz) gzip -dc "$f" | docker load ;;
      *) docker load -i "$f" ;;
    esac
  done
  [ "$found" = "1" ] || die "$dir 里没有 .tar / .tar.gz 镜像文件"
}

start_stack() {
  export APP_VERSION
  APP_VERSION=$(read_version "$INSTALL_DIR")
  load_offline_images "$INSTALL_DIR"
  compose up -d --pull never
}

replace_code() {
  dest=$1
  rm -rf "$dest/app" "$dest/deploy" "$dest/tests" "$dest/images" "$dest/docs"
  rm -f \
    "$dest/Dockerfile" \
    "$dest/docker-compose.yml" \
    "$dest/pyproject.toml" \
    "$dest/.dockerignore" \
    "$dest/.env.example" \
    "$dest/VERSION" \
    "$dest/功能说明.md" \
    "$dest/部署说明.md" \
    "$dest/发布构建标准.md" \
    "$dest/AGENT提示词.md" \
    "$dest/.gitignore"
  copy_release "$dest"
}

write_env() {
  dest=$1
  pass=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
  cat > "$dest/.env" <<EOF
DATABASE_URL=postgresql+psycopg://asset_ledger:${pass}@postgres:5432/asset_ledger
POSTGRES_USER=asset_ledger
POSTGRES_PASSWORD=${pass}
POSTGRES_DB=asset_ledger
APP_PORT=8010
PRODUCT_CODE=asset-ledger
TZ=Asia/Shanghai
EOF
  chmod 600 "$dest/.env"
}

backup_to() {
  postgres_healthy || die "本产品的 postgres 尚未就绪"
  stamp=$(date +%Y%m%d%H%M%S)
  dir="$INSTALL_DIR/backups/$stamp"
  mkdir -p "$dir"
  cp "$INSTALL_DIR/VERSION" "$dir/VERSION"
  compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d asset_ledger --no-owner --no-acl > "$dir/db.sql"
  echo "$dir"
}

assert_volume_exclusive() {
  if [ -n "${COMPOSE_PROJECT_NAME:-}" ] && [ "$COMPOSE_PROJECT_NAME" != "asset-ledger" ]; then
    echo "COMPOSE_PROJECT_NAME 必须是 asset-ledger" >&2
    exit 1
  fi
  export COMPOSE_PROJECT_NAME=asset-ledger

  for id in $(docker ps -aq); do
    [ -n "$id" ] || continue
    project=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$id" 2>/dev/null || true)
    mounts=$(docker inspect -f '{{range .Mounts}}{{println .Name}}{{end}}' "$id" 2>/dev/null || true)
    config_image=$(docker inspect -f '{{.Config.Image}}' "$id" 2>/dev/null || true)
    image_id=$(docker inspect -f '{{.Image}}' "$id" 2>/dev/null || true)
    repo_refs=$(docker image inspect -f '{{range .RepoTags}}{{println .}}{{end}}{{range .RepoDigests}}{{println .}}{{end}}' "$image_id" 2>/dev/null || true)
    refs="$config_image
$repo_refs"
    while IFS= read -r ref; do
      [ -n "$ref" ] || continue
      case "$ref" in
        sha256:*) continue ;;
      esac
      base=${ref%@*}
      base=${base%:*}
      name=${base##*/}
      if [ "$name" = "delivery-ledger" ]; then
        echo "禁止与客户交付台账同机部署" >&2
        exit 1
      fi
    done <<EOF
$refs
EOF
    if [ "$project" = "delivery-ledger" ]; then
      echo "禁止与客户交付台账同机部署" >&2
      exit 1
    fi
    while IFS= read -r mount_name; do
      if [ "$mount_name" = "delivery_ledger_pgdata" ] && [ "$project" != "asset-ledger" ]; then
        echo "禁止与客户交付台账同机部署" >&2
        exit 1
      fi
    done <<EOF
$mounts
EOF
  done

  if docker volume inspect delivery_ledger_pgdata >/dev/null 2>&1; then
    vproject=$(docker volume inspect delivery_ledger_pgdata --format '{{if .Labels}}{{index .Labels "com.docker.compose.project"}}{{end}}' 2>/dev/null || true)
    if [ "$vproject" != "asset-ledger" ]; then
      echo "卷 delivery_ledger_pgdata 不属于本产品，拒绝挂载" >&2
      exit 1
    fi
  fi
}
