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
  -e WORKBENCH_FIXTURES=/app/fixtures \
  -v "$(pwd)/reports:/app/reports:rw" \
  "$IMAGE" \
  sh -c 'for c in candidates/*/; do WORKBENCH_CANDIDATE=$(basename "$c") python -m workbench evaluate "$c" --out reports/; done'

echo ">> done; reports/ updated on host"
