#!/usr/bin/env bash
set -Eeuo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 is required for the interactive installer.' >&2
  exit 69
fi
exec python3 "$project_dir/scripts/interactive_install.py" "$@"
