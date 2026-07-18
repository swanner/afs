#!/usr/bin/env bash
set -euo pipefail

branch="${1:-main}"
message="${2:-chore: bootstrap AFS repository}"

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed." >&2
  exit 1
fi

if [ ! -d .git ]; then
  git init
  git branch -M "$branch"
  git remote add origin https://github.com/swanner/afs.git
fi

git add .
git commit -m "$message" || true
git push -u origin "$branch"
