#!/usr/bin/env bash
# Copies the staging site into the live site's repo (peaks-impact/peaks-impact.gibhub.io → peaks-office.ch),
# removes everything between <!-- STAGING:START --> and <!-- STAGING:END --> (the badge and the noindex tag),
# checks every link, image and anchor in that copy, and shows what would change. Nothing goes live unless you pass --push.
#
#   ./promote-to-live.sh           # dry run: list the changes, then put the live checkout back as it was
#   ./promote-to-live.sh --push    # also commit and push, which publishes peaks-office.ch
#
# A broken link stops both. If another site is down and a fix can't wait: SKIP_LINK_CHECK=1 ./promote-to-live.sh --push
# COMMIT_TRAILER="Co-Authored-By: …" adds that line to the live commit's message.
set -euo pipefail

STAGING="$(cd "$(dirname "$0")" && pwd)"
LIVE="${LIVE_DIR:-$HOME/Projects/peaks-website}"

git -C "$STAGING" pull -q --ff-only
git -C "$LIVE" pull -q --ff-only
if [ -n "$(git -C "$LIVE" status --porcelain)" ]; then
  echo "The live checkout at $LIVE has uncommitted changes. Clean it up first." >&2
  exit 1
fi

# The live checkout was clean a moment ago, so this only undoes the copy below
restore_live() { git -C "$LIVE" reset -q && git -C "$LIVE" checkout -q -- . && git -C "$LIVE" clean -fdq; }

# CNAME stays as it is in the live repo; the staging-only files never go live
rsync -a --delete --exclude .git --exclude CNAME --exclude README.md --exclude promote-to-live.sh --exclude check-links.py "$STAGING/" "$LIVE/"
find "$LIVE" -name '*.html' -not -path '*/.git/*' -exec perl -0pi -e 's/[ \t]*<!-- STAGING:START -->.*?<!-- STAGING:END -->\n?//gs' {} +
if grep -rq 'STAGING:' "$LIVE" --include='*.html'; then
  echo "Staging markers are left in the live copy, stopping." >&2
  restore_live
  exit 1
fi

if [ -z "${SKIP_LINK_CHECK:-}" ] && ! python3 "$STAGING/check-links.py" "$LIVE"; then
  echo "Broken links, stopping. Nothing was published." >&2
  restore_live
  exit 1
fi

git -C "$LIVE" add -A
if git -C "$LIVE" diff --cached --quiet; then
  echo "Staging and live are already the same."
  exit 0
fi
git -C "$LIVE" diff --cached --stat

if [ "${1:-}" = "--push" ]; then
  git -C "$LIVE" commit -q -m "Promote staging to live ($(git -C "$STAGING" rev-parse --short HEAD))" ${COMMIT_TRAILER:+-m "$COMMIT_TRAILER"}
  git -C "$LIVE" push -q origin main
  echo "Pushed. peaks-office.ch updates in about a minute."
else
  restore_live
  echo "Dry run: these changes would go live. Nothing was published. Run with --push to publish."
fi
