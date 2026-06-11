# Candidate Evidence Workbench

A reviewer's aid for evaluating AI Builder candidates. It reads a candidate's
own submitted materials and produces a three-part report for a **human**
interviewer:

1. **Evidence Map.** Each capability claim, matched against a rubric derived
   from the job description, marked *evidenced* (with a pointer) or *unverified*.
2. **Interview Questions.** Every unverified claim, turned into a probe.
3. **Blind-Spot Report.** What the tool could **not** verify or see.

The tool does **not** score, rank, shortlist, or reject. That is the central
design decision, and the reason for it follows.

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
eval asserts all three injection vectors are caught. The detector also handles
**cryptic / encoded payloads**: base64 blobs that decode to instructions, and
homoglyph evasion (Latin text spiked with Cyrillic or Greek lookalikes).

## Provenance

Every report is signed with an Ed25519 key. Each record in
`reports/provenance.jsonl` carries a content hash, a timestamp, the tool
version, and the signer's public key, so any report is tamper-evident and
attributable. `python evals/verify_provenance.py` re-checks them; altering a
report by one byte makes verification fail. If a report ever surfaces that this
tool did not produce, or one is changed after the fact, the signature makes it
detectable. The private key lives in `.keys/` (gitignored); the public key
travels inside each record, so verification needs no key distribution.

---

## Architecture

```
              ┌─────────────── sandbox: no network, read-only root ───────────────┐
  candidate   │ parse + extract text (PDF/MD/HTML/text)                            │
  files  ───► │   -> detect hidden/encoded content   (DETERMINISTIC security control)│
  (untrusted) │   -> extract claims                  (LLM, schema-constrained)      │
              │   -> match claims to evidence         (LLM: evidenced | unverified)  │
              │   -> assemble 3-panel report + sign   (deterministic, Ed25519)       │
              └───────────────────────────────────┬───────────────────────────────┘
                                                   ▼
                                    human reviewer decides
```

The language model extracts and matches; it never scores or decides. Detection
and assembly are deterministic. Every LLM call is written to an append-only
`audit_log.jsonl` (timestamp, model, prompt hash, output): the mechanical
precondition for the disclosure the law requires.

The pipeline degrades honestly. With no API key the deterministic stages still
run, and the Blind-Spot Report states that claim analysis did not. The threat
model and its known gaps are documented in `SECURITY.md`.

## Run it

Requires **Python 3.10+** (developed on 3.12). No API key is needed; the default
path replays committed model outputs so the tool reproduces its sample reports
on a fresh clone with zero setup.

### One command

| OS | Command |
|----|---------|
| Linux | `./run.sh` |
| macOS | `./run.sh` (tested on Linux; should work on macOS, which we could not verify) |
| Windows | `.\run.ps1` (PowerShell) |

That sets up a virtualenv, installs dependencies, runs the full gate, generates
the signed reports, and builds the viewer. Add `test` (`./run.sh test`) to run
the gate only. Then open `docs/viewer.html` in any browser.

### Or step by step

```bash
# 1. Setup (one command installs everything, including the test runner)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2. The full gate (no key, deterministic, reproducible by anyone)
python -m pytest -q                    # 11 unit tests for the detector
python evals/verify_adversarial.py     # adversarial test fixtures are accounted for
python evals/golden.py                 # golden-set expectations
python evals/detector_metrics.py       # detector precision / recall / F1
python evals/fairness_invariance.py    # output is invariant to demographic signals
python evals/verify_provenance.py      # every committed report verifies against its signature

# 3. Generate the reports yourself (no key, replays committed fixtures)
python -m workbench evaluate candidates/ --out reports/
#    reports/*.md now match the committed ones, each Ed25519-signed in reports/provenance.jsonl.

# 4. View the reports in a browser (no server, no install)
python tools/build_viewer.py           # writes docs/viewer.html
#    then open docs/viewer.html in any browser.
```

Expected from step 3:

```
c1_strong:   4 evidenced, 3 unverified, 3 questions, 2 blind spots
c2_thin:     0 evidenced, 5 unverified, 5 questions, 2 blind spots
c3_poisoned: 0 evidenced, 3 unverified, 3 questions, 2 blind spots  ⚠ ANOMALIES
```

Pre-generated reports are already committed under `reports/`, so you can read
the output without running anything. `c4_pdf_resume` is a **PDF** with hidden
white-on-white text aimed at an AI screener: the tool extracts and flags it.

### Evaluating your own candidates

Put a candidate's files (PDF, Markdown, HTML, or text) in a folder and point the
tool at it:

```bash
python -m workbench evaluate path/to/candidate_folder --out reports/
```

To process several at once, give a folder of candidate folders. This is the
"drag and drop to load" path: drop files into a folder the tool reads. PDFs are
parsed inside the hardened pipeline, so an untrusted or malicious PDF cannot
reach the network or persist. The tool deliberately does not parse dropped PDFs
in a browser.

### Optional extras

```bash
# Run the live pipeline against the real API (your own key, your own tokens):
export ANTHROPIC_API_KEY=sk-ant-...
python -m workbench evaluate candidates/ --out reports/ --live

# Analyze the (untrusted) candidate files inside a locked-down container
# (no network, read-only root, dropped capabilities). Requires Docker:
./run-sandbox.sh
```

## What I deliberately left out

Some of these are scope choices; two are on principle and I would defend keeping
them out:

* **No scoring, ranking, or shortlisting.** By design, not omission. This is the
  whole point of the tool.
* **No link fetching (on principle).** Fetching candidate-supplied URLs from the
  analysis process is an egress and SSRF risk. I declare unfetched links as a
  blind spot instead of doing it insecurely.
* **No in-browser upload-and-process (on principle).** The GUI is a read-only
  viewer. An upload UI would recreate the untrusted-input attack surface in the
  one place I cannot sandbox it.
* **No DOCX parsing yet.** PDF, Markdown, HTML, and text are supported (resumes
  usually arrive as PDF). PDFs are extracted inside the sandbox, never in a
  browser, because PDF parsers are an exploit surface. DOCX is the same kind of
  work and is the next format to add.

What I would build next, given more than a few hours: multi-reviewer calibration
with inter-rater reliability, continuous disparate-impact monitoring (the
fairness test here is point-in-time), a candidate-facing view so an applicant can
see and contest their own evidence map (the re-examination right Quebec's Law 25
anticipates), and a broader adversarial corpus (homoglyphs, RTL overrides,
base64-encoded payloads) with the residual gaps declared.

## License

See `LICENSE`. Shared publicly for the purpose of the KPMG AI Builder candidate
assessment.
