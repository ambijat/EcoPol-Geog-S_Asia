#!/usr/bin/env bash
set -euo pipefail

launcher_directory="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$launcher_directory"

if [[ ! -x ".venv/bin/python" ]]; then
    echo "IS529N launcher: .venv/bin/python was not found." >&2
    echo "Create the environment and install requirements-desktop.txt first." >&2
    exit 1
fi

exec ".venv/bin/python" -m desktop.app "$@"
