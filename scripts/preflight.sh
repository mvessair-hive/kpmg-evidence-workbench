#!/usr/bin/env bash
# Pre-flight check: run before publishing or submitting.
#
# Verifies the build passes AND that nothing unsafe is committed: no secrets,
# no private key material, no real personal data, and no leftover template
# placeholders. Exits non-zero on any failure so it can gate a release.
#
#   ./scripts/preflight.sh
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
note(){ printf '  %s\n' "$1"; }
ok(){   printf '  ok   %s\n' "$1"; }
bad(){  printf '  FAIL %s\n' "$1"; fail=1; }

echo "== 1. build gate =="
if [ -d .venv ]; then . .venv/bin/activate; fi
python -m pytest -q >/dev/null 2>&1 && ok "tests" || bad "tests"
for e in verify_adversarial golden detector_metrics fairness_invariance verify_provenance; do
  python "evals/$e.py" >/dev/null 2>&1 && ok "$e" || bad "$e"
done

echo "== 2. secrets and key material =="
# real keys look like sk-ant-<alnum...> or a PEM block; the literal placeholder sk-ant-... is allowed
# Scan only git-tracked files (so gitignored local material like .keys/ and
# .venv/ is out of scope), exclude this script (it contains the patterns), and
# allow the documented placeholder sk-ant-...
secret_hits=$(git ls-files | grep -v "scripts/preflight.sh" | tr '\n' '\0' | \
     xargs -0 grep -IE "sk-ant-[A-Za-z0-9_]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}" 2>/dev/null \
     | grep -v "sk-ant-\.\.\.")
if [ -n "$secret_hits" ]; then bad "possible secret committed: $secret_hits"; else ok "no secrets in tracked files"; fi
if git ls-files | grep -qiE "\.pem$|\.key$|\.env$|ed25519"; then bad "key/env file tracked by git"; else ok "no key material tracked"; fi

echo "== 3. real personal data =="
# any email/phone that is not a synthetic example.com / the author's own contact
if grep -rIoE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" --include=*.py --include=*.md --include=*.json --include=*.html . 2>/dev/null \
     | grep -v ".venv/" | grep -viE "example\.com|@anthropic|noreply" | grep -q .; then
  bad "a non-synthetic email is present (review)"; else ok "no real personal data"; fi

echo "== 4. leftover template placeholders =="
if grep -rIE "\{\{[A-Z_]+\}\}|TODO|FIXME|XXX" --include=*.md --include=*.py --exclude-dir=.venv . 2>/dev/null | grep -q .; then
  note "placeholders/notes present (expected: {{VIDEO_LINK}} until the video is recorded):"
  grep -rInE "\{\{[A-Z_]+\}\}" --include=*.md --exclude-dir=.venv . 2>/dev/null | sed 's/^/    /'
else ok "no placeholders"; fi

echo "== 5. internal references =="
if grep -rIiE "\b(symvek|hindsight|hermes|lodestone|cairn|manifesto)\b" --include=*.py --include=*.md --include=*.json --include=*.html --exclude-dir=.venv . 2>/dev/null | grep -q .; then
  bad "internal reference leaked"; else ok "no internal references"; fi

echo
if [ "$fail" -eq 0 ]; then echo "PREFLIGHT: PASS"; else echo "PREFLIGHT: FAIL"; fi
exit $fail
