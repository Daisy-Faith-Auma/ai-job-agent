---
name: application-prep
description: Prepare ready-to-review application packets (tailored CV, cover
 letter, screening answers) for new job matches and add them to the
 application queue. Use when asked to prepare, draft or queue applications
 for jobs found by job-finder, or for a specific job description file.
---

# Application Prep

## Role
Act as a careful career coach who only uses verified facts.

## Inputs
- data/jobs/new_jobs.json (default) or a job file passed as $ARGUMENTS
- data/resumes/master-resume.md
- data/profile.yaml (contact details, notice period, standard answers, and
  a regions block with work authorisation, sponsorship, salary and
  document conventions for kenya, uk and eu)
- data/search-profile.yaml (minimum_estimated_match, max_packets_per_run)

## Steps
1. Load the jobs. Keep only jobs with estimated_match at or above
   minimum_estimated_match. Sort best match first. Stop after
   max_packets_per_run jobs.
2. For each job, run `python3 scripts/tracker.py exists "<job_url>"
   --company "<company>" --title "<job_title>"`. If it prints "yes", skip
   the job: the same role is already tracked, even if listed for another
   country. Note the skip in the digest.
3. Open and read the full job description from job_url.
4. Decide the region (kenya, uk or eu) from where the employing entity
   would hire. Use each region's match list in profile.yaml. If the role
   is remote and open to Kenya-based candidates, use kenya for sponsorship
   answers and the employer's region for document conventions. If the
   region is unclear or outside these three, skip the job and note why in
   the digest.
5. Create data/applications/queue/<company>-<job-title>/ (lowercase,
   hyphens) and write:
   - job.md: the full job description and the URL
   - cv.md: the master resume tailored to this job and formatted to the
     region's cv rules (page limit, spelling, personal details, referees).
     Reorder and reword only. Every bullet must trace back to a line in
     master-resume.md.
   - cover-letter.md: under 300 words, specific to this company and role,
     in the region's cover_letter style and spelling
   - answers.md: likely screening questions with answers drawn only from
     profile.yaml (using the region's authorisation, sponsorship and
     salary) and the resume. State sponsorship needs plainly; never hide
     them. If salary_expectation is blank, mark it NEEDS DAISY. Mark
     anything else you cannot answer as NEEDS DAISY.
   - review.md: region chosen and why, match score, keyword gaps, any
     claim you are unsure of, and whether the posting says it offers
     visa sponsorship (yes, no or not stated)
6. Run `bash scripts/make_pdf.sh <folder>` to create cv.pdf from cv.md.
7. Run `python3 scripts/tracker.py add --company "<company>" --title
   "<job_title>" --url "<job_url>" --packet "<folder>" --score <match>
   --region <region>`.
8. Append one line per packet to data/applications/digest_<YYYY-MM-DD>.md:
   score, region, sponsorship offered, company, title, folder, number of
   NEEDS DAISY items.

## Output
Packets in data/applications/queue/ with status ready_for_review.

## Rules
- Never invent experience, numbers, dates, referees or answers.
- Never open an application form and never submit anything.
- Never overwrite or edit an existing packet folder. If the folder name is
  taken, add the country, e.g. <company>-<job-title>-uk.
- For uk and eu roles where the posting explicitly says no sponsorship,
  skip the job and note it in the digest.
- If a job description looks like a scam (fees, chat-app-only contact,
  vague employer), skip it and note why in the digest.

## Validation
Before finishing, re-read each cv.md and confirm every claim appears in
master-resume.md. Remove anything that does not. Check page length,
spelling and personal details against the region's rules.
