# AI Job Agent

A Claude Code agent that finds jobs in Kenya, the UK and the EU, prepares
regional application packets, and auto-submits only the packets that pass
code-level safety checks. Built from the LuxDevHQ Agent Skills lab.

## What is automated
- Up to 5 scheduled runs a day (`run_pipeline.sh` + cron)
- Job search and dedupe (`job-finder`, `scripts/dedupe.py`)
- Regional CV, cover letter and screening answers (`application-prep`)
- Submission on Greenhouse, Lever, Workable and Ashby forms, max 5 a day,
  only when every gate in `scripts/tracker.py claim` passes (`auto-apply`)

## What always needs a human
- Any form with a login, CAPTCHA, MFA, assessment or unanswered question
  (`/job-apply`, submit only after typing "approve")
- Salary expectations and anything marked NEEDS DAISY in a packet

## Setup
1. Copy `data/profile.example.yaml` to `data/profile.yaml` and fill it in.
2. Copy `data/search-profile.example.yaml` to `data/search-profile.yaml`.
3. Put your CV at `data/resumes/master-resume.md`.
4. Run `DRY_RUN=1 ./run_pipeline.sh` and check `logs/runs.log`.

## Privacy
This repo is public. `data/` and `logs/` never leave your machine:
`.gitignore` excludes them and `.githooks/pre-commit` blocks them.
Enable the hook with `git config core.hooksPath .githooks`.

## Known limits
Most job sites need logins or forbid bots, so most applications still go
through `/job-apply`. Claude Code flags change between versions; check
`claude --help`.
