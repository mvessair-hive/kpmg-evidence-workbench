# Sandbox for analyzing UNTRUSTED candidate materials.
#
# Candidate uploads are untrusted input by definition: a resume can carry
# hidden prompt-injection, malformed markup, or content designed to probe the
# tool. Analysis therefore runs in a container with no network access, a
# read-only root filesystem, and dropped capabilities, so even a hostile file
# cannot reach the network or persist outside the mounted report directory.
FROM python:3.12-slim

# Non-root user — the analysis process never runs with elevated privilege.
RUN useradd --create-home --uid 10001 analyst
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest

COPY workbench/ ./workbench/
COPY evals/ ./evals/
COPY tests/ ./tests/
COPY candidates/ ./candidates/
COPY fixtures/ ./fixtures/
COPY security/ ./security/
COPY reports/ ./reports/

USER analyst

# Default: deterministic test suite, adversarial-accountability check, golden
# eval. No network is needed or available (run with --network none). Reports
# land in a mounted volume. -p no:cacheprovider keeps pytest from writing a
# cache under the read-only root.
CMD ["sh", "-c", "python -m pytest -q -p no:cacheprovider && python evals/verify_adversarial.py && python evals/golden.py && python evals/detector_metrics.py && python evals/fairness_invariance.py && python evals/verify_provenance.py"]
