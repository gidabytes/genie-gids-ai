#!/usr/bin/env bash
# Publish the website by updating the gh-pages branch.
#
# Used while GitHub Actions is unavailable on the owner's account. GitHub Pages is set to
# "Deploy from a branch: gh-pages / (root)", and that branch holds ONLY the public files that
# scripts/check-site.py assembles. Run it from a clean checkout of main:
#
#   scripts/publish-gh-pages.sh --dry-run   check, assemble and show what would change
#   scripts/publish-gh-pages.sh             the same, then push to gh-pages
set -euo pipefail

dry_run=false
if [ "${1:-}" = "--dry-run" ]; then
  dry_run=true
fi

root=$(git rev-parse --show-toplevel)
cd "$root"
if [ ! -f scripts/check-site.py ] || [ ! -f privacy-statement.html ]; then
  echo "Run this inside the website repository." >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "Commit your changes first, so the published site matches a commit." >&2
  exit 1
fi
source_commit=$(git rev-parse --short HEAD)

rm -rf _site
python3 scripts/check-site.py --assemble _site

work=$(mktemp -d)
trap 'rm -rf "$work" "$root/_site"' EXIT
git clone --quiet --branch gh-pages --single-branch "$(git remote get-url origin)" "$work/pages"
find "$work/pages" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a _site/. "$work/pages/"

email=$(git config user.email || true)
if [ -n "$email" ]; then
  git -C "$work/pages" config user.email "$email"
fi
case "$email" in
  *@users.noreply.github.com) ;;
  *) echo "Note: this commit will show the address '$email'. To keep it private, set your GitHub no-reply address with: git config user.email ..." >&2 ;;
esac

git -C "$work/pages" add -A
if git -C "$work/pages" diff --cached --quiet; then
  echo "gh-pages already matches $source_commit; nothing to publish."
  exit 0
fi
git -C "$work/pages" commit --quiet -m "Publish the website from $source_commit"
git -C "$work/pages" --no-pager show --stat --format='%h %s' HEAD

if $dry_run; then
  echo "Dry run: nothing was pushed."
else
  git -C "$work/pages" push --quiet origin gh-pages
  echo "Pushed to gh-pages. GitHub Pages usually updates within a minute."
fi
