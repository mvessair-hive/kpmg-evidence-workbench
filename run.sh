#!/usr/bin/env bash
# One-command setup and run for Linux and macOS.
#   ./run.sh          set up, run the full gate, generate + view reports
#   ./run.sh test     run the gate only
# No API key needed. The default path replays committed model outputs.
#
# Verified on Linux and macOS (bash + python3).
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python)
if [ -z "${PY:-}" ]; then echo "Python 3.10+ is required and was not found on PATH."; exit 1; fi
ver=$("$PY" -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
case "$ver" in
  3.1[0-9]|3.[2-9][0-9]|[4-9].*) : ;;
  *) echo "Python 3.10+ required; found $ver at $PY."
     echo "On macOS: 'brew install python@3.12' (or python.org), then re-run ./run.sh"
     exit 1;;
esac

if [ ! -d .venv ]; then
  echo ">> creating virtualenv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
echo ">> installing dependencies"
pip install -q --upgrade pip >/dev/null
pip install -q -r requirements.txt

echo ">> gate: tests, adversarial accountability, golden eval, detector metrics, fairness, provenance"
python -m pytest -q
python evals/verify_adversarial.py
python evals/golden.py
python evals/detector_metrics.py
python evals/fairness_invariance.py
python evals/verify_provenance.py

if [ "${1:-}" = "test" ]; then echo ">> gate passed."; exit 0; fi

echo ">> generating signed reports"
python -m workbench evaluate candidates/ --out reports/
echo ">> building the report viewer"
python tools/build_viewer.py

echo
echo "Done. Open the report viewer in a browser:"
echo "  docs/viewer.html"
echo "Or read the Markdown reports under reports/."
