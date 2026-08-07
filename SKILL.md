---
name: product-map-page
description: >-
  Document one screen of a live web product from three sources — a read-only UI walkthrough,
  the source code, and the written docs — into a product map under version control.
  Produces pages/<Name>.md, reconciles it with the map, records every place where the
  documentation and the running product disagree. Run manually, one URL per session.
disable-model-invocation: true
---

# product-map-page — document one screen into the product map

A product map is a folder of markdown files describing what a product does **today** — every
screen, entity and cross-cutting mechanism — written from what runs, not from what was specified,
and kept in the repository so any human or agent can load it as context.

This skill documents **one screen per run**; run it repeatedly to build the map. `README.md` holds
the rationale, `references/` the detail — open those files when a step points at them.

## Source hierarchy — not negotiable

| Rank | Source | What it answers |
|------|--------|-----------------|
| 1 | Source code, confirmed by the UI walkthrough | How it actually works |
| 2 | Knowledge base, tracker issues, user manuals | Why it was built, what the customer was promised |

Specs were written before the build and never revised. Manuals lag the product. Issues describe
intent, not outcome. So when code and a document disagree, **the code goes into the map and the
disagreement is recorded as its own finding**. A document describing something absent from the
code is not a fact about the product — it is a candidate for the map's "Gaps" section.

## Three kinds of files

| Kind | Path | Create when |
|------|------|-------------|
| Page | `pages/<Name>.md` | One screen with its own URL |
| Entity | `entities/<Name>.md` | A domain object with fields, used by several screens |
| Function | `functions/<Name>.md` | A mechanism spanning screens: access control, notifications, guards, exports |

All three link to each other in both directions (Step 6). Templates: `references/templates/`.

## Input

1. **Screen URL** — required. Relative (`/orders`) or absolute. If not supplied, ask and stop.
2. **Focus** (optional) — a tab, block or widget to go deep on.

## Hard rule — read only

You are pointed at a running product, usually holding real data.

**Allowed:** navigating URLs, switching tabs, paginating, changing a date range, expanding blocks,
opening a dialog and closing it without submitting, screenshots, reading the DOM.

**Forbidden:** anything that writes — submitting a form, save, create, delete, apply, send,
upload, drag-and-drop, and any button whose label implies a state change on the server.

Opening a "New order" dialog to document its fields is reading. Pressing its Save button is not.
If understanding a screen genuinely requires a write, **stop and ask the operator**.

## Step 0 — configuration, and the map itself on a first run

1. **Find the config**: `map.config.yml`, normally in the map directory. Search up from the working
   directory and then across the repository — do not assume a path.
2. **No config** → run the ten-question setup interview in `references/config.md`, all of it in one
   message, write the file, confirm it with the operator. Browse nothing before that.
3. **No map yet** → create `<map_dir>/product-map.md` from `references/templates/product-map.md`
   plus empty `pages/`, `entities/`, `functions/`. Fill what is knowable from the code — purpose,
   roles, navigation — and leave the URL table to fill screen by screen. A page file with no map
   to hang on is an orphan.
4. **Read the config every run.** Two fields shape the output and are easy to forget:
   `output_language` (the map's prose; UI labels always stay in the product's own language, quoted)
   and `auth.role` (recorded in every page file, because it bounds everything observed).

Never invent credentials and never put secrets in the config or in a map file: the config holds
the path to an env file and the variable names, nothing else.

## Step 1 — reconcile with the map

Open `<map_dir>/product-map.md` and find the URL in the URL table. Record the canonical screen
name, its section number, what the map already claims, and the target filename in latin
characters (`Orders.md`, `Order-Card.md`).

- Screen missing from the table → tell the operator; add it now or at Step 6.
- `pages/<Name>.md` already exists → extend and correct it, never silently overwrite.

## Step 2 — walk the UI, read only

Goal: the factual structure — headings, tabs, columns, buttons, filters, empty states, dialogs.

Harness: `assets/playwright/`. Copy it into the project once (config `walkthrough.dir`), then

```bash
bash <walkthrough.dir>/setup.sh                                  # first run only
bash <walkthrough.dir>/run.sh --auth                             # one headed login, saved session
bash <walkthrough.dir>/run.sh --target /orders --tag orders       # walk the screen
bash <walkthrough.dir>/run.sh --target /orders --dialogs --paginate
```

Flags, selectors, environment variables and safety behaviour: `assets/playwright/README.md`.

**Read `<screenshot_dir>/<tag>.json`, not the console output.** Each snapshot writes a PNG and a
JSON file with structure plus three fields that carry findings rather than layout:

- `redirected: true` — the URL you asked for is not the URL you documented. Establish where it went
  and why before writing anything about the screen.
- `failedRequests` / `consoleErrors` — a screen whose API answers 403 or 500 renders as an empty
  list. Without these it enters the map as "no data". They belong in the page file; a reproducible
  one belongs in the tracker.
- A `WARNING` about tabs read but not clickable means tab contents were **not** captured. Extend
  the selectors, or document only what you actually saw.

A redirect, a 403 or an empty screen is data: record "not available to this role" and fill the
structure in from Step 3. If the walkthrough cannot run at all — no test environment, no
credentials, product not on the web — say so under **Status** and build from code alone. Never
present code-derived structure as UI-confirmed, and never infer screen content from its name.

## Step 3 — read the code

Refresh the checkout first — a stale clone produces confident, wrong statements — and record the
commit hash in the page file. A map entry without a commit cannot be re-verified.

```bash
git -C <code.frontend> pull --ff-only && git -C <code.frontend> log -1 --format='%h %ad'
```

Then follow `references/code-recon.md`: route → component, component and template, data calls →
the API section, models → entities, guards → access, locale files → exact labels. Search the whole
app tree, not just the screens folder: auth, layout, admin areas and modules mounted outside the
main router carry screens too.

## Step 4 — reconcile with the documentation

The walkthrough and the code give **what works**. Knowledge base, tracker, manuals and support
traffic give what was intended and what the customer was promised — and, by the difference, the
product's real backlog. **The step is not optional**: skip it and the screen is described while the
backlog stays invisible. Where to look, how to classify a finding, how to write a gap entry that
survives six months: `references/doc-sources.md`. Four of its rules to hold while reading:

- Implementation differs from the issue it shipped under → its own section in the page file.
- Specified but absent, or built differently than specified → the map's **Gaps** section, with
  source and issue key.
- A manual that tells the customer something untrue is not a gap but a defect: file it.
- **Unfinished implementation** — a stub, a mode with no form, a field with no control — is not
  automatically a defect. Confirm with the owner, and record a confirmed "intended" so it stops
  resurfacing.

Read the comments on every relevant issue. Scope changes hide there, not in the description.

## Step 5 — write the page file

Fill `references/templates/page.md` into `<map_dir>/pages/<Name>.md`; entities and functions from
their own templates.

- **Purpose** is written for whoever uses the screen, in their language. APIs and component paths
  belong in their own sections.
- **Fact and guess are visually separated.** Anything not seen in the UI and not read in the code is
  marked `> assumed, needs verification`. Guessing is prohibited; an honest gap beats a plausible
  sentence.
- **Labels** are quoted from the locale files, with the language noted.
- **Provenance in the header**: environment, role, date, commit hash, screenshot paths — written
  relative to the repository root and checked to exist.
- **Errors seen during the walkthrough** go in even when the screen looked fine.
- Link a `functions/` or `entities/` file only if it exists; otherwise name the mechanism in plain
  text and add it to the map's cross-cutting table as "to be written".

## Step 6 — wire up the links

1. **Page → map**: link the map section in the page header.
2. **Map → page**: `> Detail: [pages/<Name>.md](pages/<Name>.md)` under the section, not duplicated.
3. **Map index**: add or update the row — file, URL, status, date. This table is the map's coverage;
   keeping it current is part of the job.
4. **Page ↔ page** and **page ↔ function / entity**: both directions. When a new page appears,
   update the pages that link to it.

## Step 7 — report

Short, to the operator: which file was created or updated and what changed; what was confirmed in
the UI, what came from code, what from documents, what is still open; divergences and new entries
in "Gaps"; what the next run should cover.

## Working rules

- **One URL per session.** No parallel agents across screens: context spend grows faster than
  value, and cross-screen links get written from memory instead of from files.
- **Never write to the product.** When in doubt, ask instead of clicking.
- **The map is a repository artefact.** Commit it with the code; a map in a wiki rots like the wiki.
