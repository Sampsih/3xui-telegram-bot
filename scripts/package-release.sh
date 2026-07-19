#!/usr/bin/env bash
set -Eeuo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
version=$(tr -d '[:space:]' < "$project_dir/VERSION")
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid VERSION: $version" >&2
  exit 1
fi

stage_dir=$(mktemp -d /tmp/xui-telegram-admin-release.XXXXXX)
cleanup() { rm -rf -- "$stage_dir"; }
trap cleanup EXIT

mkdir -p "$project_dir/dist"
rsync -a \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'config/servers.json' \
  --exclude 'secrets/' \
  --exclude 'data/' \
  --exclude 'dist/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  "$project_dir/" "$stage_dir/"
cp "$project_dir/.env.example" "$stage_dir/.env.example"

archive="$project_dir/dist/xui-telegram-admin-$version.tar.gz"
tar -C "$stage_dir" -czf "$archive" .
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$(dirname -- "$archive")" && sha256sum "$(basename -- "$archive")") > "$archive.sha256"
else
  (cd "$(dirname -- "$archive")" && shasum -a 256 "$(basename -- "$archive")") > "$archive.sha256"
fi

echo "Created $archive"
echo "Created $archive.sha256"
