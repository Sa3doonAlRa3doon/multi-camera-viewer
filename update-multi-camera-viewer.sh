#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export MCV_HOME="$PWD"
if [[ ! -x .venv/bin/python ]]; then
  echo "Multi Camera Viewer is not installed in this folder." >&2
  exit 1
fi
exec .venv/bin/python manage.py update
