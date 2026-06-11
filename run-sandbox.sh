#!/usr/bin/env bash
# Analyze untrusted candidate materials inside a locked-down container.
#
# Candidate uploads are untrusted input. A resume can carry hidden
# prompt-injection, malformed markup, or content meant to probe the tool.
# Analysis runs with no network, a read-only root filesystem, dropped
# capabilities, and resource caps, so even a hostile file cannot reach the
# network or persist outside the mounted reports directory.
#
# Security posture (each flag is a deliberate control):
#   --network none      no egress: a poisoned resume cannot phone home
#   --read-only         immutable root fs: nothing the file does persists
#   --cap-drop ALL      no Linux capabilities
#   --security-opt no-new-privileges
#   --pids-limit / --memory   caps against a decompression/loop bomb
#   tmpfs /tmp          the only writable scratch, wiped on exit
#   reports/ is the single writable bind mount.
set -euo pipefail
cd "$(dirname "$0")"

# Docker is the only prerequisite for this optional script, and it is NOT needed
# to evaluate the tool. The full pipeline, tests, reports, and viewer all run
# without Docker via ./run.sh. This script only demonstrates the hardened
# sandbox that isolates untrusted-file parsing.
if ! command -v docker >/dev/null 2>&1; then
  echo "This optional script needs Docker, which was not found on PATH."
  echo "Docker is NOT required to evaluate the tool: run ./run.sh instead."
  echo "Install Docker Desktop (macOS/Windows) or Docker Engine (Linux) to use the sandbox."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker is installed but the daemon is not running. Start Docker Desktop, then re-run."
  echo "(Docker is NOT required to evaluate the tool: ./run.sh works without it.)"
  exit 1
fi

IMAGE="candidate-evidence-workbench:sandbox"
LOCK=(--network none --read-only --cap-drop ALL --security-opt no-new-privileges
      --pids-limit 128 --memory 512m --tmpfs /tmp:rw,size=64m)

echo ">> building sandbox image"
docker build -q -t "$IMAGE" . >/dev/null

echo ">> gate: tests + adversarial accountability + golden eval (read-only, no network)"
docker run --rm "${LOCK[@]}" "$IMAGE"

echo ">> generating reports from candidate materials (reports/ is the only writable mount)"
mkdir -p reports
docker run --rm "${LOCK[@]}" \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd)/reports:/app/reports:rw" \
  "$IMAGE" \
  python -m workbench evaluate candidates/ --out reports/

echo ">> done; reports/ updated on host"
