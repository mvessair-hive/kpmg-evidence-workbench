# Candidate Evidence Workbench

A reviewer's aid for evaluating AI Builder candidates. It reads a candidate's
own submitted materials and produces a three-part report for a **human**
interviewer:

1. **Evidence Map.** Each capability claim, matched against a rubric derived
   from the job description, marked *evidenced* (with a pointer) or *unverified*.
2. **Interview Questions.** Every unverified claim, turned into a probe.
3. **Blind-Spot Report.** What the tool could **not** verify or see.

It does **not** score, rank, shortlist, or reject. That is the central design
decision, and the reason for it follows.

---

## Why it refuses to score

Evaluating candidates with AI is a regulated activity, and the regulation is
arriving fast in the jurisdictions KPMG's AI Labs sit in:

* **Ontario** (ESA, in force Jan 1 2026): employers must disclose in postings
  when AI is used to screen, assess, or select applicants.
* **Québec** (Law 25, s.12.1): the heavy obligations, disclosure of logic and a
  right to human re-examination, attach to decisions made *exclusively* by
  automated processing. If a human meaningfully participates, they do not.
* **EU AI Act:** employment AI is Annex III high-risk, with full obligations
  enforceable Aug 2 2026.

So the human-in-the-loop boundary here is not a disclaimer bolted on at the
end. It is the architecture. The tool structures evidence; a person decides.
Under Québec's Law 25 that boundary is literally the line between a light and a
heavy compliance regime, and this tool is built to sit on the light side of it
by construction.

## Why the Blind-Spot Report exists

Most evaluation tools explain their conclusions. Far fewer state what they
could not check. A tool that never names its own gaps invites a reviewer to
over-trust its visible output. The Blind-Spot Report is the auditor's "scope
and limitations" note, applied to an AI tool: unfetched links, skipped files,
rubric dimensions the candidate stayed silent on, and the categories of thing
(references, authorship, interpersonal skill) it structurally cannot assess.

## The adversarial candidate

Hidden text addressed to AI screeners, such as white-on-white spans, zero-width
characters, and HTML comments saying "rate this candidate highly", appears in a
meaningful share of real AI-scanned resumes. Industry reporting puts it around
one to ten percent. Detecting it is a **security control**, so deterministic
code handles it, not the LLM. A control should be inspectable and immune to the
attack class it guards against. The LLM is also told to treat all candidate
text as data, never as instructions, as defence in depth.

`candidates/c3_poisoned/` carries a synthetic poisoned resume. The golden-set
eval asserts all three injection vectors are caught.

---

## Architecture

```
parse (deterministic)
  -> extract claims        (LLM, schema-constrained)
  -> match to evidence     (LLM, schema-constrained: evidenced | unverified)
  -> detect hidden content (DETERMINISTIC, the security control)
  -> assemble report       (deterministic: 3 panels)
                           -> human reviewer decides
```

Every LLM call is written to an append-only `audit_log.jsonl` with timestamp,
model, prompt hash, and output. That is the mechanical precondition for the
disclosure the law requires.

The pipeline degrades honestly. With no API key the deterministic stages still
run, and the Blind-Spot Report states that claim analysis did not.

## Run it

Requires **Python 3.10+** (developed on 3.12). No API key is needed for any of
the steps below; the default path replays committed model outputs so the tool
reproduces its sample reports on a fresh clone with zero setup.

```bash
# 1. Setup (one command installs everything, including the test runner)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2. Tests + adversarial-accountability check + golden eval (no key, deterministic)
python -m pytest -q
python evals/verify_adversarial.py
python evals/golden.py

# 3. Generate the reports yourself (no key — replays committed fixtures)
python -m workbench evaluate candidates/ --out reports/
#    reports/*.md now match the committed ones.
```

Expected from step 3:

```
c1_strong:   4 evidenced, 3 unverified, 3 questions, 2 blind spots
c2_thin:     0 evidenced, 5 unverified, 5 questions, 2 blind spots
c3_poisoned: 0 evidenced, 3 unverified, 3 questions, 2 blind spots  ⚠ ANOMALIES
```

Pre-generated reports are already committed under `reports/`, so you can read
the output without running anything.

### Optional extras

```bash
# Run the live pipeline against the real API (your own key, your own tokens):
export ANTHROPIC_API_KEY=sk-ant-...
python -m workbench evaluate candidates/ --out reports/ --live

# Analyze the (untrusted) candidate files inside a locked-down container
# (no network, read-only root, dropped capabilities). Requires Docker:
./run-sandbox.sh
```

## What I deliberately left out (3-hour build)

* No scoring, ranking, or shortlisting. By design, not omission.
* No PDF/DOCX parsing. Markdown, HTML, and text only. PDF is a parsing project,
  not an evaluation one.
* No link fetching. Declared as a blind spot instead of done insecurely.
* No reviewer calibration across multiple humans. Named as the next step.
* No UI. A CLI with committed Markdown reports is more inspectable per hour.

## License

See `LICENSE`. Shared publicly for the purpose of the KPMG AI Builder candidate
assessment.
