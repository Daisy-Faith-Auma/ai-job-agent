#!/usr/bin/env bash
# check_private.sh : exit 1 if any staged file is personal data.
# Used by the pre-commit hook and by git_push.sh. The repo is public.
ALLOWED='^data/(profile|search-profile)\.example\.yaml$'
BAD=$(git diff --cached --name-only | grep -E '^(data/|logs/|\.browser-profile/|\.env$)' | grep -vE "$ALLOWED" || true)
if [ -n "$BAD" ]; then
  echo "BLOCKED: these personal files must never go to the public repo:" >&2
  echo "$BAD" >&2
  echo "Unstage them with: git restore --staged <file>" >&2
  exit 1
fi
exit 0
