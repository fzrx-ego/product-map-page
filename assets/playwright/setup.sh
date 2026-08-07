#!/usr/bin/env bash
# One-time setup for the walkthrough harness. Idempotent, and non-destructive on re-runs:
# an existing .gitignore is appended to, never replaced.
set -euo pipefail

PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.62.1}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

[ -f package.json ] || cat > package.json <<'JSON'
{
  "name": "product-map-walkthrough",
  "private": true,
  "description": "Read-only UI walkthrough harness for the product-map-page skill"
}
JSON

npm install -D "@playwright/test@${PLAYWRIGHT_VERSION}"
npx playwright install chromium

touch .gitignore
while IFS= read -r line; do
  [ -z "$line" ] && continue
  grep -qxF "$line" .gitignore || printf '%s\n' "$line" >> .gitignore
done <<'GITIGNORE'
node_modules/
.auth/
.test-results/
# screenshots of a live product may hold customer data
screenshots/
GITIGNORE

chmod +x run.sh setup.sh 2>/dev/null || true

echo
echo "Ready. Next:"
echo "  bash run.sh --auth                         # log in once, save the session"
echo "  bash run.sh --target /orders --tag orders  # document a screen"
echo
echo "If the map's screenshot directory sits outside this folder, gitignore it there too —"
echo "run.sh warns when it is not ignored."
