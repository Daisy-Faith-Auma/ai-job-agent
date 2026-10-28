"""Application tracker: the single source of truth for application state.

Usage:
  python3 scripts/tracker.py add --company C --title T --url U --packet DIR [--score N] [--region kenya|uk|eu]
  python3 scripts/tracker.py exists URL
  python3 scripts/tracker.py next
  python3 scripts/tracker.py get APP_ID
  python3 scripts/tracker.py set APP_ID STATUS [--ref REF] [--note NOTE]
  python3 scripts/tracker.py list [--status STATUS]
  python3 scripts/tracker.py claim      # next packet eligible for auto-apply, or {}
  python3 scripts/tracker.py quota      # auto-submissions left today
"""
import argparse, csv, json, os, sys, hashlib
from datetime import datetime
from urllib.parse import urlsplit

DB = "data/applications.csv"
FIELDS = ["app_id", "company", "job_title", "job_url", "region", "score", "status",
          "packet_dir", "prepared_at", "updated_at", "confirmation_ref", "notes"]
STATUSES = {"ready_for_review", "filling", "awaiting_approval", "auto_filling",
            "needs_review", "submitted", "skipped", "failed"}
SEARCH_PROFILE = "data/search-profile.yaml"
DEFAULTS = {"auto_submit_enabled": False, "auto_submit_min_match": 85,
            "max_auto_submits_per_day": 5,
            "auto_submit_domains": ["boards.greenhouse.io", "job-boards.greenhouse.io",
                                    "jobs.lever.co", "apply.workable.com",
                                    "jobs.ashbyhq.com"]}


def settings():
    """Read auto-apply settings from search-profile.yaml (simple key: value lines)."""
    cfg = dict(DEFAULTS)
    if not os.path.exists(SEARCH_PROFILE):
        return cfg
    for line in open(SEARCH_PROFILE):
        if ":" not in line or line.strip().startswith("#"):
            continue
        k, v = (x.strip() for x in line.split("#")[0].split(":", 1))
        if k not in cfg or not v:
            continue
        if k == "auto_submit_domains":
            cfg[k] = [d.strip().strip("'\"") for d in v.strip("[]").split(",") if d.strip()]
        elif k == "auto_submit_enabled":
            cfg[k] = v.lower() in ("true", "yes", "1")
        else:
            cfg[k] = int(v)
    return cfg


def submits_today(rows):
    today = datetime.now().date().isoformat()
    return sum(1 for r in rows
               if r["status"] in ("submitted", "auto_filling")
               and r["updated_at"].startswith(today)
               and "auto" in r["notes"])


def blockers(r, cfg):
    """Return reasons a packet is NOT safe to auto-submit (empty list = eligible)."""
    why = []
    if float(r["score"] or 0) < cfg["auto_submit_min_match"]:
        why.append(f'score {r["score"]} below {cfg["auto_submit_min_match"]}')
    if r["region"] not in ("kenya", "uk", "eu"):
        why.append("region unknown")
    host = urlsplit(r["job_url"].lower()).netloc
    if not any(host == d or host.endswith("." + d) for d in cfg["auto_submit_domains"]):
        why.append(f"domain {host} not on allowlist")
    pk = r["packet_dir"]
    for f in ("cv.pdf", "answers.md", "cover-letter.md"):
        if not os.path.exists(os.path.join(pk, f)):
            why.append(f"missing {f}")
    ans = os.path.join(pk, "answers.md")
    if os.path.exists(ans) and "NEEDS DAISY" in open(ans).read():
        why.append("answers.md has NEEDS DAISY items")
    return why


def now():
    return datetime.now().isoformat(timespec="minutes")


def url_key(u):
    p = urlsplit((u or "").strip().lower())
    host = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
    return hashlib.sha1((host + p.path.rstrip("/")).encode()).hexdigest()[:10]


def load():
    if not os.path.exists(DB):
        return []
    with open(DB, newline="") as f:
        return list(csv.DictReader(f))


def save(rows):
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    tmp = DB + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, DB)


def find(rows, app_id):
    for r in rows:
        if r["app_id"] == app_id:
            return r
    sys.exit(f"No application with id {app_id}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    for k in ("company", "title", "url", "packet"):
        a.add_argument(f"--{k}", required=True)
    a.add_argument("--score", default="")
    a.add_argument("--region", default="", choices=["", "kenya", "uk", "eu"])
    sub.add_parser("exists").add_argument("url")
    sub.add_parser("next")
    sub.add_parser("get").add_argument("app_id")
    s = sub.add_parser("set")
    s.add_argument("app_id")
    s.add_argument("status", choices=sorted(STATUSES))
    s.add_argument("--ref", default="")
    s.add_argument("--note", default="")
    l = sub.add_parser("list")
    l.add_argument("--status")
    sub.add_parser("claim")
    sub.add_parser("quota")
    args = ap.parse_args()

    rows = load()

    if args.cmd == "exists":
        print("yes" if any(r["app_id"] == url_key(args.url) for r in rows) else "no")

    elif args.cmd == "add":
        app_id = url_key(args.url)
        if any(r["app_id"] == app_id for r in rows):
            print(f"skip: {app_id} already tracked")
            return
        rows.append({"app_id": app_id, "company": args.company,
                     "job_title": args.title, "job_url": args.url,
                     "region": args.region,
                     "score": args.score, "status": "ready_for_review",
                     "packet_dir": args.packet, "prepared_at": now(),
                     "updated_at": now(), "confirmation_ref": "", "notes": ""})
        save(rows)
        print(f"added {app_id}")

    elif args.cmd == "next":
        ready = [r for r in rows if r["status"] in ("ready_for_review", "needs_review")]
        ready.sort(key=lambda r: float(r["score"] or 0), reverse=True)
        print(json.dumps(ready[0], indent=2) if ready else "{}")

    elif args.cmd == "get":
        print(json.dumps(find(rows, args.app_id), indent=2))

    elif args.cmd == "set":
        r = find(rows, args.app_id)
        if r["status"] == "submitted":
            sys.exit(f"{args.app_id} is already submitted; not changing it")
        if args.status == "submitted" and r["status"] not in ("awaiting_approval", "auto_filling", "filling"):
            sys.exit(f"{args.app_id} was never filled; refusing to mark submitted")
        if args.status == "submitted" and not args.ref:
            sys.exit("Refusing to mark submitted without --ref (confirmation evidence)")
        r["status"], r["updated_at"] = args.status, now()
        if args.ref:
            r["confirmation_ref"] = args.ref
        if args.note:
            r["notes"] = (r["notes"] + "; " if r["notes"] else "") + args.note
        save(rows)
        print(f"{args.app_id} -> {args.status}")

    elif args.cmd == "list":
        for r in rows:
            if not args.status or r["status"] == args.status:
                print(f'{r["app_id"]}  {r["status"]:<18} {r.get("region",""):<6} {r["score"]:>3}  '
                      f'{r["company"]} | {r["job_title"]}')


    elif args.cmd == "quota":
        cfg = settings()
        print(max(0, cfg["max_auto_submits_per_day"] - submits_today(rows)))

    elif args.cmd == "claim":
        cfg = settings()
        if not cfg["auto_submit_enabled"] or os.path.exists("AUTO_APPLY_OFF"):
            print("{}"); return
        if submits_today(rows) >= cfg["max_auto_submits_per_day"]:
            print("{}"); return
        ready = [r for r in rows if r["status"] == "ready_for_review"]
        ready.sort(key=lambda r: float(r["score"] or 0), reverse=True)
        for r in ready:
            why = blockers(r, cfg)
            if why:
                r["status"], r["updated_at"] = "needs_review", now()
                r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "not auto: " + ", ".join(why)
                continue
            r["status"], r["updated_at"] = "auto_filling", now()
            r["notes"] = (r["notes"] + "; " if r["notes"] else "") + "auto"
            save(rows)
            print(json.dumps(r, indent=2)); return
        save(rows)
        print("{}")


if __name__ == "__main__":
    main()
