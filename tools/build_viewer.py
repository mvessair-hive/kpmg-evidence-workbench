"""Build a single self-contained viewer.html for the reports.

No server, no dependencies, no install: a reviewer double-clicks the file and
sees every candidate report rendered as a tabbed, color-coded interface. The
data is embedded inline, so it works from file:// with nothing running.

This is a VIEWER, deliberately not an uploader. The tool treats candidate files
as untrusted and analyzes them in a sandbox; an in-browser upload-and-process UI
would recreate that attack surface in the one place we cannot sandbox it. So the
GUI shows results; the analysis stays in the hardened pipeline.
"""
from __future__ import annotations

import html
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from workbench.pipeline import evaluate_candidate  # noqa: E402
from workbench.schemas import ClaimStatus  # noqa: E402


def report_to_dict(r) -> dict:
    return {
        "id": r.candidate_id,
        "files": r.files_examined,
        "anomalies": [{"kind": a.kind, "where": f"{a.source_file}:{a.line}", "why": a.explanation} for a in r.anomalies],
        "findings": [
            {"text": f.claim.text, "dim": f.claim.rubric_dimension, "status": f.status.value,
             "detail": f.evidence_pointer or f.rationale}
            for f in r.findings
        ],
        "questions": [q.question for q in r.questions],
        "blind_spots": [{"cat": b.category, "detail": b.detail} for b in r.blind_spots],
        "evidenced": len(r.evidenced),
        "unverified": len(r.unverified),
    }


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Candidate Evidence Workbench</title>
<style>
 body{font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#1a1a1a;background:#f6f7f9}
 header{background:#00338d;color:#fff;padding:18px 28px}
 header h1{margin:0;font-size:20px} header p{margin:4px 0 0;opacity:.85;font-size:13px}
 .wrap{max-width:900px;margin:0 auto;padding:22px}
 .legend{background:#fff;border:1px solid #e3e7ee;border-radius:8px;padding:11px 14px;margin-bottom:16px;font-size:12.5px;color:#586273;line-height:2}
 .legend b{color:#33415c} .legend .pill{margin:0 2px}
 .lg-warn{color:#a02320;font-weight:600;margin-left:6px} .lg-blind{background:#eef2fb;color:#33415c;padding:2px 8px;border-radius:20px;font-size:11px;font-weight:600;margin-left:6px}
 .lg-sig{color:#1d7a3f;font-weight:600;margin-left:6px}
 .ov-h{font-size:15px;color:#00338d;margin:0 0 4px} .ov-sub{font-weight:400;color:#8a93a3;font-size:12.5px}
 table.ov{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e7ee;border-radius:8px;overflow:hidden;margin:8px 0 18px;font-size:13.5px}
 table.ov th{background:#f2f4f8;color:#33415c;text-align:left;padding:8px 12px;font-size:12px}
 table.ov td{padding:9px 12px;border-top:1px solid #eef0f4}
 table.ov tr.row{cursor:pointer} table.ov tr.row:hover{background:#f6f9ff}
 table.ov tr.active td{background:#eef4ff}
 .flagcell{color:#a02320;font-weight:600} .cleancell{color:#1d7a3f}
 .back{display:inline-block;margin:0 0 10px;color:#00338d;cursor:pointer;font-size:13px}
 .card{background:#fff;border:1px solid #e3e7ee;border-radius:10px;padding:0;overflow:hidden;display:none}
 .card.active{display:block}
 .disclaimer{background:#eef2fb;color:#33415c;font-size:13px;padding:10px 18px;border-bottom:1px solid #e3e7ee}
 .banner{background:#fdecea;color:#a02320;padding:12px 18px;font-weight:600;border-bottom:1px solid #f5c6c0}
 section{padding:14px 18px;border-bottom:1px solid #eef0f4}
 section h3{margin:0 0 10px;font-size:15px;color:#00338d}
 .claim{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #f2f4f7;align-items:flex-start}
 .pill{font-size:11px;padding:2px 8px;border-radius:20px;white-space:nowrap;font-weight:600}
 .evidenced{background:#e7f6ec;color:#1d7a3f} .unverified{background:#fcf3e3;color:#9a6700}
 .claim .body{flex:1} .claim .dim{color:#8a93a3;font-size:12px}
 .claim .detail{color:#586273;font-size:13px}
 ol{margin:6px 0 0;padding-left:22px} ol li{margin:6px 0}
 .anom{font-size:13px;padding:6px 0;border-bottom:1px solid #f2f4f7}
 .anom code{background:#f4f4f4;padding:1px 5px;border-radius:3px;color:#a02320}
 .blind{background:#f8f9fb} .blind .bs{padding:6px 0;font-size:13.5px;border-bottom:1px solid #eef0f4}
 .bs b{color:#33415c} .count{color:#586273;font-size:13px;margin-top:8px}
 footer{max-width:900px;margin:0 auto;padding:14px 22px;color:#8a93a3;font-size:12px}
</style></head><body>
<header><h1>Candidate Evidence Workbench</h1>
<p>Structures evidence for a human reviewer. Does not score, rank, or recommend. A person decides.</p></header>
<div class="wrap">
 <div class="legend">
  <b>Legend:</b>
  <span class="pill evidenced">&#10003; evidenced</span> claim has checkable support in the materials
  <span class="pill unverified">&#10067; unverified</span> plausible but not checkable here (becomes an interview question)
  <span class="lg-warn">&#9888; anomaly</span> hidden / encoded text aimed at an AI screener (a human decides what it means)
  <span class="lg-blind">blind spot</span> something the tool could not see or verify
  <span class="lg-sig">&#128274; signed</span> report is Ed25519-signed and tamper-evident
 </div>
 <h2 class="ov-h">Candidate overview <span class="ov-sub" id="ovsub"></span></h2>
 <table class="ov" id="overview"><thead><tr><th>Candidate</th><th>Files</th><th>Flags</th><th>Evidenced</th><th>Unverified</th></tr></thead><tbody id="ovbody"></tbody></table>
 <div id="cards"></div>
</div>
<footer>Read-only viewer. The analysis runs in a sandboxed pipeline; this page only displays its output.</footer>
<script>
const DATA = __DATA__;
const ovbody = document.getElementById('ovbody'), cards = document.getElementById('cards');
document.getElementById('ovsub').textContent =
  `(${DATA.length} submissions). Click a row to review. Flags mark manipulation attempts to check first, not a quality ranking.`;

function showCard(i){
  document.querySelectorAll('.card').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('tr.row').forEach(x=>x.classList.remove('active'));
  document.getElementById('card-'+i).classList.add('active');
  document.getElementById('row-'+i).classList.add('active');
  document.getElementById('card-'+i).scrollIntoView({behavior:'smooth',block:'start'});
}

DATA.forEach((r, i) => {
  const tr = document.createElement('tr'); tr.className='row'; tr.id='row-'+i;
  const flags = r.anomalies.length
    ? `<span class="flagcell">\\u26a0 ${r.anomalies.length}</span>`
    : `<span class="cleancell">clean</span>`;
  tr.innerHTML = `<td><b>${r.id}</b></td><td>${r.files.length}</td><td>${flags}</td>`+
                 `<td>${r.evidenced}</td><td>${r.unverified}</td>`;
  tr.onclick = () => showCard(i);
  ovbody.appendChild(tr);

  const c = document.createElement('div'); c.className='card'; c.id='card-'+i;
  let h = `<div class="back" onclick="document.getElementById('overview').scrollIntoView({behavior:'smooth'})">\\u2191 back to overview</div>`;
  h += `<div class="disclaimer">Files examined: ${r.files.join(', ')||'none'}</div>`;
  if (r.anomalies.length) h += `<div class="banner">\\u26a0 ${r.anomalies.length} anomaly flag(s). Information for the reviewer, not a rejection. A human decides what they mean.</div>`;
  h += `<section><h3>1. Evidence Map</h3>`;
  if (!r.findings.length) h += `<div class="count">No claims extracted (see Blind-Spot Report).</div>`;
  r.findings.sort((a,b)=>a.status.localeCompare(b.status)).forEach(f => {
    h += `<div class="claim"><span class="pill ${f.status}">${f.status==='evidenced'?'\\u2705 evidenced':'\\u2753 unverified'}</span>
      <div class="body">${esc(f.text)}<div class="dim">${f.dim}</div><div class="detail">${esc(f.detail)}</div></div></div>`;
  });
  if (r.findings.length) h += `<div class="count"><b>${r.evidenced} evidenced &middot; ${r.unverified} unverified.</b> Unverified is not untrue; it means the materials do not let a reviewer check it.</div>`;
  h += `</section>`;
  h += `<section><h3>2. Interview Questions</h3>`;
  h += r.questions.length ? '<ol>'+r.questions.map(q=>`<li>${esc(q)}</li>`).join('')+'</ol>' : '<div class="count">None.</div>';
  h += `</section>`;
  if (r.anomalies.length){ h += `<section><h3>\\u26a0 Anomaly Detail</h3>`;
    r.anomalies.forEach(a=>h+=`<div class="anom"><b>${a.kind}</b> <code>${a.where}</code>: ${esc(a.why)}</div>`); h+=`</section>`; }
  h += `<section class="blind"><h3>3. Blind-Spot Report: what this tool could NOT see</h3>`;
  r.blind_spots.forEach(b=>h+=`<div class="bs"><b>${b.cat}</b>: ${esc(b.detail)}</div>`);
  h += `</section>`;
  c.innerHTML = h; cards.appendChild(c);
});
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML;}
</script></body></html>"""


def run() -> int:
    out = Path(tempfile.mkdtemp(prefix="viewer-"))
    data = []
    for c in sorted((ROOT / "candidates").iterdir()):
        if c.is_dir():
            data.append(report_to_dict(evaluate_candidate(c, out)))
    page = PAGE.replace("__DATA__", json.dumps(data))
    dest = ROOT / "docs" / "viewer.html"
    dest.write_text(page, encoding="utf-8")
    print(f"wrote {dest} ({len(page)} bytes, {len(data)} candidates). Open it in any browser, no server needed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
