---
name: workday-application
description: Use when the user asks to apply, fill out, or submit a job application on a Workday-hosted career site (URLs containing myworkdayjobs.com, or a "Apply on the company site" link from an aggregator like zapply.jobs that lands on one) — drives the multi-step Workday apply flow with Claude in Chrome, filling what's knowable from profile.json and the tailored resume, and stopping for the user on anything legal, sensitive, or irreversible.
---

# Workday Application

## Overview

Workday's external-candidate apply flow is a fixed 7-step wizard: **Create
Account/Sign In → Autofill with Resume → My Information → My Experience →
Application Questions → Voluntary Disclosures → Self Identify → Review →
Submit**. The steps are consistent across companies (different Workday
tenants, same underlying product), so the same navigation technique applies
everywhere — only the specific questions and dropdown options vary.

**Core principle:** autofill what's verifiably true from `profile.json` and
the tailored resume PDF; stop and ask the user for anything else — personal
data not on file, legal attestations, demographic self-ID, and the final
Submit. Never guess at a fact about the candidate to keep the flow moving.

**Prerequisite data:** a `profile.json` at the repo root with the
candidate's non-resume personal details:

```json
{
    "email": "person@example.com",
    "ethnicity": "Not Hispanic or Latino",
    "race": "Asian/South Asian",
    "gender": "Male",
    "pronouns": "He/Him",
    "Address": "123 Main St, City, ST 00000",
    "phone type": "Mobile",
    "phone": "+1 (555) 555-5555"
}
```

If it doesn't exist yet, ask the user for these fields once and offer to
save them there so future applications don't re-ask. Treat this file as
private — never put its contents in a request to an external service beyond
the application form itself.

## Workflow

### 0. Load the browser tools and the resume

In one `ToolSearch` call: `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__file_upload,mcp__claude-in-chrome__tabs_create_mcp`.

Get the compiled, tailored resume PDF for this posting (e.g. from the job's
branch if this repo also has `tailor-resume`: `git show <branch>:resume.pdf
> <file>`). **File uploads only work from this session's own working
directory or scratchpad** — a path under the OS temp dir that isn't the
scratchpad is rejected. Copy the PDF into the repo root under a throwaway
name, upload it, then delete the copy once the upload succeeds.

### 1. Create Account / Sign In

Fill the email field from `profile.json`. **Never set or type a password
yourself** — ask the user which email to use (default to the one in
`profile.json`) and tell them to enter and confirm the password themselves
in the open browser tab, then wait for them to confirm before continuing.

### 2. Autofill with Resume

Upload the resume PDF to the file input (`file_upload` tool with the
element's `ref` from `find`, never by clicking the input — that opens a
native picker the agent can't see). Click Continue once it shows
"Successfully Uploaded!".

### 3. My Information

Workday's resume parser often leaves this page blank even though later
steps get auto-populated — don't assume blank means broken, just fill what
you can see: name, city, phone usually parse correctly, but confirm before
depending on it. Fill in from `profile.json`:
- Email, phone number, phone type → direct copy
- City/State from the `Address` field
- **Street address and postal code**: if `profile.json`'s `Address` string
  doesn't parse unambiguously into "Address Line 1" + postal code, leave
  those two fields for the user to type directly in the browser rather than
  guessing — tell them which fields and wait.

"How did you hear about us" dropdowns are typically a multi-level picker
with no real text filter (see gotcha below); pick the closest real source
(e.g. the job board the posting was found through) — this is marketing
metadata, not a legal attestation, reasonable approximation is fine.

### 4. My Experience

This is populated from the uploaded resume via Workday's own parser, which
is unreliable in two specific ways — always verify before continuing:

1. **Duplicate work-experience entries.** The parser sometimes emits each
   job twice (e.g. 3 real roles become 6 entries, with the duplicates
   missing their Company field). Scroll through every entry and diff dates/
   titles; delete exact date+title duplicates via each entry's "Delete"
   link, starting from the highest-numbered duplicate so indices don't
   shift under you mid-deletion.
2. **Missing Company field on entries with no explicit employer line** in
   the resume source (e.g. a "Research Assistant" bullet under a thesis
   with no `\subtext{}` line) — fill it in from context (the institution
   named in the bullet text), don't leave it blank.

Check Education entries the same way (degree level, field of study, GPA)
and the Skills list (auto-suggested from the resume — usually fine as-is).
Websites (LinkedIn/GitHub) are usually correctly parsed from the resume's
header; verify with `get_page_text` or a screenshot rather than re-typing.

### 5. Application Questions

These are almost entirely legal attestations or personal facts the agent
cannot know: age/work authorization, visa sponsorship, prior employment
with the company or its corporate relatives, military service (self and
spouse), relatives employed there, contractor/dealer history, relocation
willingness. **Batch them into one or two `AskUserQuestion` calls before
touching any dropdown** — don't answer "Yes" to work authorization or "No"
to sponsorship on the user's behalf even when it seems obviously true from
their resume (US-based prior employers, etc.).

### 6. Voluntary Disclosures

Gender / Race-Ethnicity / Veteran status dropdowns map directly from
`profile.json` (`gender`, `race` + `ethnicity`, and "not a veteran" unless
told otherwise) — fill these without asking, they're already on file.

The **Terms and Conditions / arbitration agreement checkbox** is different:
it waives the candidate's right to a jury trial for employment disputes.
Flag this specifically and get an explicit yes before checking it, even
though the user already approved "applying" in general — this is a distinct
legal waiver, not implied by that earlier go-ahead.

### 7. Self Identify

The CC-305 federal disability self-identification form (name, date,
Yes/No/decline checkbox) is a separate voluntary disclosure from the
Voluntary Disclosures step even though the content looks similar — it has
its own Name/Date fields to fill and its own Yes/No/decline question. Ask
the user for their disability status the same way as the legal questions in
step 5; don't infer it.

### 8. Review and Submit

Read the whole review page with `get_page_text` (it summarizes every prior
step) and sanity-check it against what you filled — this is the only place
all 7 steps' answers are visible together, so it catches a field that
silently reverted or a dropdown that didn't register. Summarize it
concisely back to the user (name/contact, each role, education, the
attestation answers, demographic selections) and get an explicit "yes,
submit" before clicking Submit — this is the one truly irreversible action
in the whole flow.

## Gotchas

- **Combobox search boxes that don't filter.** Several Workday dropdowns
  (Field of Study, skills, "how did you hear about us" sub-menus) render a
  "Search" text box that looks like a type-ahead filter but doesn't
  actually narrow the list when you type into it — `form_input` setting the
  value directly has the same non-effect. The real mechanism is scrolling
  the always-alphabetical list to the right letter range. Don't waste
  retries on typing; scroll instead.
- **No exact match in a controlled-vocabulary dropdown** (e.g. "Computer
  Science" isn't a literal option, only "Computer and Information Science",
  "Computer Engineering", etc.). Pick the closest real option rather than
  leaving it unset — these are categorical fields than need *a* value, not
  character-exact string matches.
- **A click that looks like it failed may have just re-triggered a
  different control** — e.g. clicking to "close" an open dropdown can land
  on and reopen a different field's dropdown if the page reflowed after the
  previous action. Screenshot after every dropdown interaction rather than
  chaining blind clicks.
- **"Back" from inside the wizard prompts "Discard Application?"** — this
  is destructive (loses all entered data), not simple navigation. Never
  click through it reflexively to "double check" a prior step; use
  `get_page_text` on the current/Review page instead wherever possible.

## Quick reference

| Step | What to source from `profile.json` / resume | What to ask the user |
|---|---|---|
| Create Account | email | password (they type it) |
| Autofill with Resume | resume PDF upload | — |
| My Information | name, city, state, phone, email | street address / postal code if ambiguous |
| My Experience | work history, education, skills, websites (verify parser dupes) | — |
| Application Questions | — | every question (legal attestations) |
| Voluntary Disclosures | gender, race/ethnicity, veteran status | arbitration-agreement checkbox |
| Self Identify | name, date | disability status |
| Review | — | final submit go-ahead |

## Common mistakes

- **Answering a legal/demographic question from "it's probably true"**
  (e.g. assuming work authorization because prior employers were US
  companies) instead of asking. Always ask.
- **Checking the arbitration-agreement box as part of general "yes, apply"
  permission.** It needs its own explicit confirmation.
- **Trusting the resume-parsed work experience list at face value.** Always
  scroll every entry and check for duplicate date+title pairs with blank
  Company fields before moving past "My Experience".
- **Retyping a value into a combobox search box expecting it to filter.**
  It won't — scroll the alphabetical list instead.
- **Uploading straight from the scratchpad/temp directory.** Copy the file
  into the repo working directory first; scratchpad paths are rejected by
  `file_upload`.
- **Clicking "Back" to "verify" a previous step.** It prompts a destructive
  discard dialog; read the Review page instead.
