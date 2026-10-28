#!/usr/bin/env bash
# git_push.sh "<message>" : commit and push code, skills and docs to the
# PUBLIC GitHub repo. Personal data is ignored by .gitignore and blocked by
# scripts/check_private.sh. Never fails the pipeline; see logs/git.log.
set -uo pipefail
cd "$HOME/ai-job-agent"
mkdir -p logs
MSG="${1:-update}"
log() { echo "$(date '+%F %H:%M') $*" >> logs/git.log; }

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { log "skip: not a git repo"; exit 0; }

git add -A
if ! bash scripts/check_private.sh; then
  git reset -q
  log "REFUSED push ($MSG): personal files were staged"
  exit 0
fi
if git diff --cached --quiet; then
  log "nothing to commit ($MSG)"
  exit 0
fi
git commit -q -m "$MSG" || { log "commit failed ($MSG)"; exit 0; }
if git pull -q --rebase && git push -q; then
  log "pushed: $MSG"
else
  log "push failed ($MSG); will retry on next push"
fi
