# Security model and its limits

This tool processes untrusted input (candidate-submitted files), so it has a
threat model, and the threat model has gaps. Stating them is the same discipline
the tool applies to candidate claims: name what you cannot verify.

## What the tool defends against

- **Hidden text aimed at an AI screener.** White-on-white spans, tiny fonts,
  `display:none`, zero-width characters, HTML comments. Detected deterministically.
- **Encoded payloads.** Base64 blobs that decode to instructions, and homoglyph
  evasion (Latin text spiked with Cyrillic or Greek lookalikes).
- **Hidden text inside PDF and DOCX files.** Documents are extracted to text and
  scanned, so a white-on-white instruction inside a PDF or a DOCX run is caught
  like one in a web page.
- **Untrusted-file risk.** Parsing (including PDF parsing, an exploit surface)
  runs in a container with no network, a read-only root filesystem, dropped
  capabilities, and resource caps, so a hostile file cannot reach the network or
  persist.
- **Prompt injection of the model.** Defence in depth: even if a payload reaches
  the language model, it is instructed to treat all candidate text as data, never
  as instructions, and the model never makes a terminal decision.
- **Tampering with output.** Every report is Ed25519-signed and verifiable.
- **Self-generated adversarial content.** Test fixtures that carry payloads are
  fingerprinted in a manifest; the build fails if any undeclared adversarial
  content appears.

## What it does NOT catch (known gaps)

- **Semantic injection without trigger phrases.** The detector is pattern-based.
  An instruction phrased as ordinary prose, with no keyword and no obfuscation,
  can pass the deterministic layer. The model-side "treat text as data" rule and
  the no-decision architecture are the backstop, not the detector.
- **Novel encodings.** It decodes base64 and flags mixed-script tokens. It does
  not yet handle hex, ROT-N, right-to-left override tricks, or Unicode tag
  characters. Each is a known follow-up.
- **Text rendered as an image.** Instructions inside an embedded image are not
  read; the tool does not run OCR.
- **A malicious file format exploit** that defeats the parser itself. The sandbox
  contains the blast radius (no network, no persistence), but containment is not
  prevention.
- **Truthful-looking fabrication.** A candidate who invents a plausible,
  specific, consistent story will have it extracted as a claim and marked
  unverified, not flagged. That is correct: the tool surfaces it as an interview
  question, and a human probes it. The tool detects manipulation of the screener,
  not dishonesty about the candidate.

## Why over-flagging is acceptable here

The detector errs toward flagging. That is safe because nothing is automated:
every flag is shown to a human, with no reject, score, or rank attached. A false
positive costs a moment of a reviewer's attention, not a wrongly rejected
candidate. The same property is why the gaps above are tolerable in a first
version: the human, not the detector, is the decision-maker.

## Reporting

This is an assessment artifact, not a deployed system. For a real deployment,
security issues would go to a monitored channel and the adversarial corpus would
be expanded continuously.
