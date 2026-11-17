---
name: tailor-resume
description: Use when the user gives one or more job postings (URLs or pasted text) and asks to tailor, adapt, or customize this resume for them — creates one git branch per posting with a reworded (never fabricated) resume and logs the application in metadata.json.
---

# Tailor Resume

## Overview

Each job posting gets its own branch off `main`, built by reordering and
lightly rewording the *existing, truthful* content in `sections/*.tex` to
foreground what that posting asks for — never by inventing skills, tools,
titles, or years of experience the candidate doesn't have. Every branch is
logged as a row in `metadata.json` on `main` so there's a durable record of
what was applied to, when, and from which posting.

**Core principle:** truthful re-emphasis, not rewriting. If a posting needs
something genuinely absent from `sections/experience.tex` or
`sections/skills.tex`, say so to the user instead of adding it.

## Workflow

For each job posting, in order:

### 1. Get the job description

Fetch the URL with WebFetch. If it 403s or comes back as only a header/apply
link (seen with some ATS mirrors and `zapply.jobs`-style aggregators), retry
with `curl -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"`
and grep the saved HTML (or its `application/ld+json` block) for the posting
text. If the user pasted several URLs, fetch all of them in one batch of
parallel tool calls before doing anything else — don't fetch-then-edit one
at a time.

**Watch for duplicate postings.** Different URLs (e.g. two different
`zapply.jobs/jobs/<uuid>/` links) sometimes resolve to the identical job.
Compare the fetched title + company before creating a branch; if two links
are the same posting, make one branch, not two, and tell the user.

Extract: company, exact role title, location, required vs. preferred
qualifications, responsibilities, named tools/frameworks, years-of-experience
asks, and salary if listed. A role's own job ID (e.g. a Workday requisition
number, or the UUID in a `zapply.jobs` URL) counts as the "unique job ID" for
branch naming if the posting exposes one.

### 2. Decide branch name and log the application

Run the bundled script from the repo root, on a clean `main`:

```bash
python .claude/skills/tailor-resume/scripts/add_job_entry.py \
  --company "Apple" \
  --role "Machine Learning Engineer" \
  --url "https://jobs.apple.com/en-us/details/..." \
  --job-id "ads-ml-platform-2026"   # omit if the posting has no stable ID
```

It prints the branch name and appends a row to `metadata.json` (schema
below) — it does not touch git. Then:

```bash
git add metadata.json
git commit -m "Log job application: <Company> <Role>"
git checkout -b <branch-name-printed-above>
```

Branch name shape: `job-YYYYMMDD-<company-slug>-<role-slug>[-<job-id-slug>]`
— e.g. `job-20261117-apple-ml-engineer-ads-ml-platform-2026`. Always let the
script generate it; don't hand-roll the slug.

**metadata.json schema** (array of entries, lives at repo root, tracked on
`main` so the full application history survives even if a branch is later
deleted):

```json
[
  {
    "date": "2026-11-17",
    "company": "Apple",
    "role": "Machine Learning Engineer",
    "job_id": "ads-ml-platform-2026",
    "job_url": "https://jobs.apple.com/en-us/details/...",
    "branch": "job-20261117-apple-ml-engineer-ads-ml-platform-2026"
  }
]
```

### 3. Tailor the content, on the new branch

Edit, in this order:

1. **`resume.tex`**: set `\role` to a title matching the posting's seniority
   (close paraphrase is fine, e.g. "Senior AI/ML Engineer"; don't invent a
   title the candidate has never held). Uncomment `\input{sections/objective}`.
2. **`sections/objective.tex`**: replace with a 1–2 sentence summary built
   only from real experience, using the posting's own vocabulary where it
   genuinely overlaps (e.g. "ML lifecycle", "agentic workflows", "MLOps").
   Keep it to ~2 lines of rendered text — this section has no spare room
   (see step 5).
3. **`sections/experience.tex`**: reorder bullets within each role so the
   ones most relevant to this posting come first. Reword for emphasis and
   to swap in the posting's terms for the same real fact (e.g. "bundling
   algorithm" → "bundling/recommendation algorithm" for a ranking role) —
   never add a tool, metric, or outcome that isn't already in the bullet.
   Merging two related bullets into one is fine and often necessary for
   page budget (step 5).
4. **`sections/skills.tex`**: reorder and relabel the category names (e.g.
   "ML & AI" → "Ranking & Retrieval") to match the posting's framing, using
   only skills already listed on `main`. Don't add a tool the candidate
   hasn't used, even if the posting asks for it.
5. **`sections/activities.tex`**: trim only if needed for page budget (next
   step); don't rewrite its claims.

### 4. Compile and enforce the one-page budget

```bash
pdflatex -interaction=nonstopmode resume.tex
grep "Output written" resume.log
```

`main`'s resume is tuned to fill exactly one page with the objective section
commented out. Turning the objective on adds ~3 lines, which reliably pushes
the document to 2 pages on the first pass — **this is expected, not an
error.** Pull it back to one page by merging/shortening bullets (step 3) and
trimming `sections/activities.tex` to 3 lines, then recompile. Don't stop
until `grep "Output written"` reports `(1 page, ...)`. Spot-check the layout
with `pdftotext -layout resume.pdf -` before committing — a label misaligned
with its row in that dump is usually just a text-extraction artifact of the
multi-row skills table, not a real rendering bug; open the PDF if unsure.

### 5. Commit and return to main

```bash
git add -A
git commit -m "Tailor resume for <Company> <Role>

<one or two sentences on what was reordered/reframed and why>

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git checkout main -- .
git checkout main
```

The `git checkout main -- .` before switching branches discards the
regenerated build artifacts (`resume.aux`, `.log`, `.out`) so the next
branch starts from a clean `main` working tree.

### 6. Report honestly

Tell the user, per posting: the branch name, and a one-line honest read on
fit — call out any requirement (years of experience, a named tool, a
citizenship/clearance/location constraint) that the tailoring couldn't close
without fabricating. A posting that's a weak fit should still get a branch,
but say so plainly rather than overstating the match.

## Quick reference

| Step | Command |
|---|---|
| Name branch + log it | `python .claude/skills/tailor-resume/scripts/add_job_entry.py --company ... --role ... --url ... [--job-id ...]` |
| Commit the log, branch | `git add metadata.json && git commit -m "..." && git checkout -b <branch>` |
| Compile | `pdflatex -interaction=nonstopmode resume.tex` |
| Check page count | `grep "Output written" resume.log` |
| Reset build junk, return | `git checkout main -- . && git checkout main` |

## Common mistakes

- **Adding a skill/tool the candidate hasn't used** because the posting asks
  for it. Don't. Reorder and reframe what's real; flag the gap to the user
  instead.
- **Leaving the resume at 2 pages.** Enabling the objective section always
  requires cutting ~3 lines elsewhere first. Always verify with `grep
  "Output written"` before committing.
- **Hand-rolling the branch name** instead of using the script — this skips
  the duplicate-branch check and the metadata.json entry, so the registry
  and the branches drift apart.
- **Forgetting `git checkout main -- .`** before starting the next posting —
  leftover build-artifact diffs (`resume.aux`, `.log`, `.out`) bleed into the
  next branch's first commit.
- **Treating two different posting URLs as different jobs** without
  checking — some job boards mirror the same listing at multiple UUIDs.
