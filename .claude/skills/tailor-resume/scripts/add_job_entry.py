#!/usr/bin/env python
"""Compute a branch name for a job application and append it to metadata.json.

Does NOT touch git. Run this on a clean `main`, then commit the updated
metadata.json, then `git checkout -b <branch>` using the printed name.

Usage:
    python add_job_entry.py --company "Apple" --role "Machine Learning Engineer" \
        --url "https://example.com/jobs/123" [--job-id 5b113396] [--metadata metadata.json]
"""
import argparse
import datetime
import json
import os
import re
import sys


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--job-id", default=None, help="Posting's own job ID, if the listing provides one")
    parser.add_argument("--metadata", default="metadata.json")
    parser.add_argument("--date", default=None, help="Override date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    date = args.date or datetime.date.today().isoformat()
    date_compact = date.replace("-", "")
    company_slug = slugify(args.company)
    role_slug = slugify(args.role)

    branch = f"job-{date_compact}-{company_slug}-{role_slug}"
    if args.job_id:
        branch += f"-{slugify(args.job_id)}"

    entry = {
        "date": date,
        "company": args.company,
        "role": args.role,
        "job_id": args.job_id,
        "job_url": args.url,
        "branch": branch,
    }

    if os.path.exists(args.metadata):
        with open(args.metadata, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    if any(e.get("branch") == branch for e in data):
        print(f"ERROR: branch '{branch}' already exists in {args.metadata}", file=sys.stderr)
        print("Add --date, or a --job-id, to disambiguate.", file=sys.stderr)
        return 1

    data.append(entry)

    with open(args.metadata, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    # Only line meant to be parsed by the caller.
    print(branch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
