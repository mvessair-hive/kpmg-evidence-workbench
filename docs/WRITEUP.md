# AI Builder Case Study: Candidate Evidence Workbench

**Mitchell Vessair**
**Role applied for: AI Builder, Manager**

**Artifact:** https://github.com/mvessair-hive/kpmg-evidence-workbench
**Video (3 min):** {{VIDEO_LINK}}

---

## How I framed the problem

The brief asks me to build something that evaluates an AI Builder well, using
the job description as source material. The first decision was the real one:
what does "evaluate well" mean.

The obvious build is a scorer. Feed it a resume, return a fit score or a
ranking. I deliberately did not build that, and the reason is the whole point
of my submission. Scoring candidates with AI is a regulated activity in every
jurisdiction KPMG's AI Labs sit in, and the regulation turns on one line:

- **Ontario** (ESA, in force Jan 1 2026): an employer must disclose when AI is
  used to screen, assess, or select applicants.
- **Quebec** (Law 25, s.12.1): the heavy obligations, disclosing the decision
  logic and granting a right to human re-examination, attach to decisions made
  *exclusively* by automated processing. If a human meaningfully participates,
  they do not.
- **EU AI Act**: employment AI is Annex III high-risk, with full obligations
  enforceable Aug 2 2026.

So I reframed the task. Evaluating a candidate well does not mean producing a
verdict. It means giving a human reviewer better evidence to reach their own.
The tool structures evidence; a person decides. Under Quebec's Law 25 that
boundary is literally the line between a light and a heavy compliance regime,
and I built the tool to sit on the light side of it by construction, not by
policy.

## What I built

A command-line tool that reads a candidate's submitted materials and produces a
three-part report for a human interviewer:

1. **Evidence Map.** Every capability claim, matched against a rubric I derived
   from the job description, marked *evidenced* with a pointer to the proof, or
   *unverified*. Most claims in most packages are unverified, and that is
   normal. Unverified does not mean untrue. It means the materials do not let a
   reviewer check it.
2. **Interview Questions.** Each unverified claim becomes a specific probe, so
   the interview spends its time where the evidence is thin.
3. **Blind-Spot Report.** What the tool could not verify or see: links it did
   not fetch, files it skipped, rubric dimensions the candidate was silent on,
   and the categories it structurally cannot assess, such as references and
   interpersonal skill.

The third panel is the part I am most deliberate about. Most evaluation tools
explain their conclusions. Far fewer state what they could not check. A tool
that never names its own gaps invites a reviewer to over-trust its visible
output. The Blind-Spot Report is the auditor's scope-and-limitations note,
applied to an AI tool.

## Key choices and tradeoffs

**The LLM extracts and matches; it never decides.** Deterministic code does the
parsing, the anomaly detection, and the report assembly. The language model
only reads claims and checks them against the materials. This keeps the model
away from any terminal judgment and makes the pipeline auditable.

**Injection defense is deterministic, not a prompt.** Hidden text addressed to
AI screeners (white-on-white spans, zero-width characters, HTML comments saying
"rate this candidate highly") appears in a meaningful share of real AI-scanned
resumes. Detecting it is a security control, so deterministic code handles it.
A control should be inspectable and immune to the attack class it guards
against. The detector also handles cryptic payloads: base64 blobs that decode to
instructions, and homoglyph evasion (Latin text spiked with Cyrillic or Greek
lookalikes). The language model is told to treat all candidate text as data,
never as instructions, as a second layer. The detector deliberately over-flags,
because every flag is shown to a human with no automated action attached, so a
false positive costs almost nothing. Its quality is measured, not assumed:
precision, recall, and F1 on a labeled corpus, reported by the test suite.

**Every report is signed.** Each report is Ed25519-signed, with a content hash,
a timestamp, and the signer's public key recorded in a provenance ledger. In a
system that informs decisions about people, "who produced this, and has it been
altered" has to be answerable. Altering a signed report by one byte makes
verification fail. A production version would use the organization's managed
keys and a post-quantum scheme.

**Untrusted input is analyzed in a sandbox, including PDF and DOCX.** Candidate
uploads are untrusted by definition, and resumes arrive as PDF or DOCX, two of
the most exploited parsing surfaces in software. So extraction happens inside the
same hardened pipeline as the rest of the analysis: a container with no network
access, a read-only root filesystem, and dropped privileges. A malicious
document cannot reach the network or persist, and the hidden-text detector runs
on the extracted text, so white-on-white instructions inside a PDF or a DOCX are
caught the same way they are in a web page. This is also why I do not parse
dropped files in a browser: the parsing belongs in the sandbox. I treat
self-generated adversarial test fixtures the same way: they are fingerprinted in
a manifest, and a checker fails the build if any adversarial content is present
that is not accounted for.

**Measured, not asserted.** The injection detector is a security control, so I
report its numbers rather than claim it works: precision, recall, and F1 on a
labeled corpus that includes adversarial negatives (emphatic self-description,
the literal word "stage", legitimate inline styling). Building that corpus found
a real miss, a "disregard your evaluation rubric" phrasing the first version let
through, which I then fixed. I also test fairness mechanically: identical
resumes with swapped names, pronouns, and schools produce byte-identical output,
so demographic identity cannot change a result.

**Built for a batch, with a read-only viewer.** A recruiter reviews many
candidates at once, so the tool processes a whole folder in one run, and the
viewer opens on an overview: every submission, its flag status, and its
evidenced and unverified counts, with click-through to each report. The flag
column surfaces manipulation attempts to check first; it is deliberately not a
quality ranking, since ranking is the human's job. The viewer is read-only. I
did not build an upload-and-process web UI, because it would recreate the
untrusted-input attack surface in the one place I cannot sandbox it. Showing
results in a browser is safe; parsing untrusted uploads there is not.

## Risks and what I would do with more time

- **Extraction quality is unproven beyond my golden set.** I tested against a
  small, deliberately diverse synthetic set. Real materials are messier. The
  next step is a larger, labeled evaluation set and measured extraction accuracy.
- **Reviewer calibration.** Two reviewers reading the same evidence map may
  still probe differently. A production version would study and reduce that
  variance.
- **No OCR for image-based resumes.** PDF, DOCX, Markdown, HTML, and text are
  supported, parsed inside the sandbox since document parsers are an exploit
  surface. A scanned-image resume, or text baked into a picture, is not read;
  OCR is the next ingestion step.
- **Fairness auditing.** The tool avoids demographic inference and does not
  score, which removes the most direct bias vector, but a real deployment needs
  ongoing disparate-impact monitoring.

## How I used AI, and which decisions were mine

I built this with an agentic coding environment (Claude Code) that I run with
persistent memory, a code-intelligence layer, and evaluation guardrails I
maintain. The AI wrote most of the code under my direction and generated the
synthetic candidates and the reference model outputs committed in the repo.

The decisions were mine: reframing the task away from scoring, grounding that
choice in the specific regulations above, making human-in-the-loop the
architecture rather than a disclaimer, adding the Blind-Spot Report, handling
injection as a deterministic control, and sandboxing untrusted input. Partway
through the build I also caught myself confusing an adversarial test file I had
generated for a possible external one, which is the exact failure this tool is
built to prevent, so I added a fingerprint manifest that makes self-generated
adversarial content accountable. The judgment, the tradeoffs, and the line about
what the tool must refuse to do are the parts I own and can defend.
