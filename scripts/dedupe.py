"""dedupe.py : keep only jobs we have never seen before.

Usage: python3 scripts/dedupe.py data/jobs/candidates.json

Compares every job against data/seen_jobs.csv using two keys:
  1. the cleaned-up URL (host + path, no www., no ?utm=... tracking)
  2. company + job title + location (catches the same job re-posted elsewhere)
  3. company + job title (catches one role listed separately per country)
Writes fresh jobs to data/jobs/new_jobs.json and records them as seen.
"""
import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlsplit

SEEN = "data/seen_jobs.csv"
NEW = "data/jobs/new_jobs.json"
FIELDS = ["url_key", "ctl_key", "company", "job_title", "location",
          "job_url", "first_seen"]


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def url_key(u):
    p = urlsplit((u or "").strip().lower())
    host = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
    return h(host + p.path.rstrip("/")) if host else ""


def ctl_key(j):
    parts = [str(j.get(k) or "").strip().lower()
             for k in ("company", "job_title", "location")]
    return h("|".join(parts)) if any(parts) else ""


def ct_key(j):
    parts = [str(j.get(k) or "").strip().lower() for k in ("company", "job_title")]
    return h("ct|" + "|".join(parts)) if all(parts) else ""


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 scripts/dedupe.py data/jobs/candidates.json")

    seen = set()
    if os.path.exists(SEEN):
        with open(SEEN, newline="") as f:
            for r in csv.DictReader(f):
                seen.update(k for k in (r["url_key"], r["ctl_key"], ct_key(r)) if k)

    with open(sys.argv[1]) as f:
        jobs = json.load(f)

    new = []
    for j in jobs:
        keys = {url_key(j.get("job_url")), ctl_key(j), ct_key(j)} - {""}
        if not keys or keys & seen:
            continue  # already seen, or no usable key
        seen |= keys
        new.append(j)

    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    first = not os.path.exists(SEEN)
    with open(SEEN, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if first:
            w.writeheader()
        for j in new:
            w.writerow({"url_key": url_key(j.get("job_url")),
                        "ctl_key": ctl_key(j),
                        "company": j.get("company"),
                        "job_title": j.get("job_title"),
                        "location": j.get("location"),
                        "job_url": j.get("job_url"),
                        "first_seen": datetime.now().isoformat(timespec="minutes")})

    os.makedirs(os.path.dirname(NEW), exist_ok=True)
    with open(NEW, "w") as f:
        json.dump(new, f, indent=2)

    print(f"{len(jobs)} found | {len(new)} new | {len(jobs) - len(new)} already seen")


if __name__ == "__main__":
    main()
