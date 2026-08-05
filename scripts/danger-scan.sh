#!/bin/bash
# Danger static scan: exit 1 if any dangerous pattern is found in source files.
# NOTE: this script excludes itself from scanning to avoid self-matching.
set -u
cd "$(dirname "$0")/.."
PATTERNS=(
  'rm[[:space:]]+-rf[[:space:]]+/'
  'base64[[:space:]]+-d.*\|.*sh'
  'curl.*\|.*sh'
  'wget.*-O-.*\|.*sh'
  'chmod[[:space:]]+-R[[:space:]]+777[[:space:]]+/'
)
HITS=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  for pat in "${PATTERNS[@]}"; do
    if grep -qE "$pat" "$f"; then
      echo "[DANGER] $f matches: $pat"
      HITS=$((HITS + 1))
    fi
  done
done < <(find . -type f \( -name '*.py' -o -name '*.sh' -o -name '*.js' \) \
         -not -path './.git/*' -not -path './scripts/danger-scan.sh' -not -path './tests/test_malware.py')
if [ "$HITS" -gt 0 ]; then
  echo "[BLOCKED] $HITS dangerous pattern(s) found"
  exit 1
fi
echo "[OK] no dangerous patterns"