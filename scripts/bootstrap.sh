#!/usr/bin/env bash
set -Eeuo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"

install -d -m 0700 data secrets config

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 0600 .env
  echo 'Created .env from .env.example'
fi

if [[ ! -f config/servers.json ]]; then
  cp config/servers.example.json config/servers.json
  chmod 0600 config/servers.json
  echo 'Created config/servers.json from the example inventory'
fi

touch data/.gitkeep secrets/.gitkeep
chmod 0700 data secrets

echo 'Bootstrap complete. Edit .env and config/servers.json, then run: make validate'
