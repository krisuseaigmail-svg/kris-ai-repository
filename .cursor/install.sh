#!/usr/bin/env bash
# Idempotent Cloud Agent install: refresh project dependencies if a manifest exists.
# Must terminate; do not start servers, watchers, or databases here.
set -euo pipefail

if [[ -f pnpm-lock.yaml ]]; then
  pnpm install --frozen-lockfile
elif [[ -f yarn.lock ]]; then
  yarn install --frozen-lockfile
elif [[ -f package-lock.json ]]; then
  npm ci
elif [[ -f package.json ]]; then
  npm install
elif [[ -f uv.lock ]]; then
  uv sync
elif [[ -f requirements.txt ]]; then
  python3 -m pip install -r requirements.txt
elif [[ -f pyproject.toml ]]; then
  python3 -m pip install -e .
elif [[ -f go.mod ]]; then
  go mod download
elif [[ -f Cargo.lock ]]; then
  cargo fetch --locked
elif [[ -f Cargo.toml ]]; then
  cargo fetch
else
  echo "No dependency manifest found; skipping install."
fi
