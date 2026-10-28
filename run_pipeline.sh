#!/usr/bin/env bash
# run_pipeline.sh : one scheduled run. Find, dedupe, prepare, auto-apply.
# Hard caps: 5 runs per day (this file) and max_auto_submits_per_day (tracker).
# Kill switch: touch AUTO_APPLY_OFF   Dry run: DRY_RUN=1 ./run_pipeline.sh
set -euo pipefail
cd "$HOME/ai-job-agent"
mkdir -p logs data/resumes data/jobs data/applications/queue
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || echo "$HOME/.local/bin/claude")}"
TODAY=$(date +%F)
STAMP=$(date +%H%M)
DRY="${DRY_RUN:-0}"

RUNS=$(grep -c "^$TODAY .* ok:" logs/runs.log 2>/dev/null || true)
if [ "${RUNS:-0}" -ge 5 ]; then
  echo "$TODAY $(date +%H:%M) skipped: daily limit of 5 runs reached" >> logs/runs.log
  bash scripts/git_push.sh "run $TODAY $STAMP: skipped, daily limit"
  exit 0
fi

# 1. Find and dedupe
"$CLAUDE_BIN" -p "Use the job-finder skill. Follow it exactly, including running
scripts/dedupe.py. Report only new jobs. Do not apply to anything." \
  --allowedTools "Read,Write,WebSearch,WebFetch,Bash(python3 scripts/dedupe.py *)" \
  --max-turns 40 \
  > "logs/find_${TODAY}_${STAMP}.md" 2>&1

NEW=$(python3 -c 'import json;print(len(json.load(open("data/jobs/new_jobs.json"))))')
bash scripts/git_push.sh "run $TODAY $STAMP: find, $NEW new jobs"

# 2. Prepare packets for new matches
if [ "$NEW" -gt 0 ]; then
  "$CLAUDE_BIN" -p "Use the application-prep skill on data/jobs/new_jobs.json.
Follow it exactly. Do not open application forms or submit anything." \
    --allowedTools "Read,Write,WebFetch,Bash(python3 scripts/tracker.py *),Bash(bash scripts/make_pdf.sh *)" \
    --max-turns 60 \
    > "logs/prep_${TODAY}_${STAMP}.md" 2>&1
  bash scripts/git_push.sh "run $TODAY $STAMP: prepared packets"
fi

# 3. Auto-apply (only if code-level gates allow it)
QUOTA=$(python3 scripts/tracker.py quota)
SUBMITTED=0
if [ ! -f AUTO_APPLY_OFF ] && [ "$QUOTA" -gt 0 ]; then
  BEFORE=$(python3 scripts/tracker.py list --status submitted | wc -l)
  PROMPT="/auto-apply"
  [ "$DRY" = "1" ] && PROMPT="/auto-apply DRY_RUN"
  "$CLAUDE_BIN" -p "$PROMPT" \
    --mcp-config mcp-auto.json \
    --allowedTools "Read,Write,mcp__playwright,Bash(python3 scripts/tracker.py *)" \
    --max-turns 80 \
    > "logs/apply_${TODAY}_${STAMP}.md" 2>&1 || true
  AFTER=$(python3 scripts/tracker.py list --status submitted | wc -l)
  SUBMITTED=$((AFTER - BEFORE))
  bash scripts/git_push.sh "run $TODAY $STAMP: auto-apply, $SUBMITTED submitted"
fi

READY=$(python3 scripts/tracker.py list --status needs_review | wc -l | tr -d ' ')
echo "$TODAY $(date +%H:%M) ok: $NEW new jobs, $SUBMITTED submitted, $READY need review" >> logs/runs.log
bash scripts/git_push.sh "run $TODAY $STAMP: done"
