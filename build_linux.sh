#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$project_dir/.venv/bin/python" ]]; then
  build_python="$project_dir/.venv/bin/python"
elif [[ -n "${PYBASE:-}" ]]; then
  build_python="$PYBASE"
elif command -v python3 >/dev/null 2>&1; then
  build_python=python3
else
  build_python=python
fi

exec "$build_python" "$project_dir/scripts/build.py" "$@"
