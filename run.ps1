# One-command setup and run for Windows (PowerShell).
#   .\run.ps1          set up, run the full gate, generate + view reports
#   .\run.ps1 test     run the gate only
# No API key needed. The default path replays committed model outputs.
#
# If PowerShell blocks the script, allow it for this session with:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Pause at the end so a double-clicked window does not vanish before output is read.
trap { Write-Host "`nError: $_" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

# Works on both Windows PowerShell 5.1 and PowerShell 7+ (no 7-only `??` operator).
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) { Write-Error "Python 3.10+ is required and was not found on PATH."; exit 1 }
$ver = & $py.Source -c "import sys;print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
$parts = $ver.Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
  Write-Error "Python 3.10+ required; found $ver. Install from python.org, then re-run .\run.ps1"
  exit 1
}

if (-not (Test-Path .venv)) {
  Write-Host ">> creating virtualenv"
  & $py.Source -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
Write-Host ">> installing dependencies"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

Write-Host ">> gate: tests, adversarial accountability, golden eval, detector metrics, fairness, provenance"
python -m pytest -q
python evals/verify_adversarial.py
python evals/golden.py
python evals/detector_metrics.py
python evals/fairness_invariance.py
python evals/verify_provenance.py

if ($args[0] -eq "test") { Write-Host ">> gate passed."; Read-Host "Press Enter to close"; exit 0 }

Write-Host ">> generating signed reports"
python -m workbench evaluate candidates/ --out reports/
Write-Host ">> building the report viewer"
python tools/build_viewer.py

Write-Host ""
Write-Host "Done. Open the report viewer in a browser:"
Write-Host "  docs\viewer.html"
Write-Host "Or read the Markdown reports under reports\."
Write-Host ""
Read-Host "Press Enter to close"
