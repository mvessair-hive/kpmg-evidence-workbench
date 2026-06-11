# IntakeRouter — design excerpt (included as work sample)

*(SYNTHETIC ARTIFACT — fictional system, generated for evaluation-tool testing)*

## Problem
Claims intake email was hand-triaged by 4 adjusters (~90 min/day each).
Misroutes added 2–3 days of latency on ~8% of claims.

## Agent/tool boundary
The LLM classifies and extracts (claim type, policy id, urgency signals).
Everything that ACTS is deterministic code:
- queue assignment = lookup table over the classification
- approval gate: any claim with estimated exposure > $5,000, or model
  self-reported confidence < 0.8, is held for human approval — the agent
  cannot release it
- no write access to the claims system; it drafts, a human commits

## Evaluation
- 240-email labeled set built from anonymized historical mail (compliance
  approved); nightly regression in CI
- per-class precision/recall tracked; deploys blocked if macro-F1 drops > 2pts
- adversarial slice: 18 emails crafted with misleading subject lines and
  embedded instructions ("urgent — route to fast-track"); the agent must
  classify from body content, not follow embedded directives

## A failure I caught
v0.3 silently routed bilingual (FR/EN) emails to the wrong queue 31% of the
time — the eval set had only 4 French samples. Fix: expanded the slice to 40,
added language detection before classification, re-baselined. This is why I
don't trust evals I haven't audited for coverage.
