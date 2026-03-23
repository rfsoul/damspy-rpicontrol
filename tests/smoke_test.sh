#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "AGENTS.md"
  "README.md"
  "doc_map.md"
  "docs/agent_commands.md"
  "Makefile"
  "pyproject.toml"
  "src/damspy_rpicontrol/__init__.py"
  "src/damspy_rpicontrol/__main__.py"
  "src/damspy_rpicontrol/main.py"
  "src/damspy_rpicontrol/models.py"
  "src/damspy_rpicontrol/rxcc_device.py"
  "src/damspy_rpicontrol/templates/index.html"
  "tests/test_models.py"
  "tests/test_rxcc_device.py"
  "tests/test_app.py"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required repository file: $f" >&2
    exit 1
  fi
done

echo "Smoke checks passed."
