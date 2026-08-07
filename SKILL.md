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

A product map is a folder of markdown files describing what a product does **today**:
every screen, every entity, every cross-cutting mechanism. It is written from what runs,
not from what was specified. It lives in the repository, so any human or agent can load it
as context instead of re-deriving the product from code and hallway conversations.

This skill documents **one screen per run**. Run it repeatedly to build the map.

Read `README.md` in this folder for the rationale and the layout of a finished map.

## Source hierarchy — not negotiable

| Rank | Source | What it answers |
|------|--------|-----------------|
| 1 | Source code, confirmed by the UI walkthrough | How it actually works |
| 2 | Knowledge base, tracker issues, user manuals | Why it was built, what the customer was promised |

Specs were written before the build and never revised. Manuals lag the product. Issues
describe intent, not outcome. So when code and a document disagree, **the code goes into
the map and the disagreement is recorded as its own finding** (Step 4). A document
describing something absent from the code is not a fact about the product — it is a
candidate for the map's "Gaps" section.

## Three kinds of files

| Kind | Path | Create when |
|------|------|-------------|
| Page | `pages/<Name>.md` | One screen with its own URL |
| Entity | `entities/<Name>.md` | A domain object with fields, used by several screens |
| Function | `functions/<Name>.md` | A mechanism spanning screens: access control, notifications, auth guards, exports |

All three link to each other **in both directions** (Step 6).

---

## Input

1. **Screen URL** — required. Relative (`/orders`) or absolute. If not supplied, ask and stop.
2. **Focus** (optional) — a tab, block or widget to go deep on.

---

## Hard rule — read only

You are pointed at a running product, usually holding real data.

**Allowed:** navigating URLs, switching tabs, paginating, changing a date range, expanding
blocks, opening a dialog and closing it without submitting, screenshots, reading the DOM.

**Forbidden:** anything that writes — submitting a form, save, create, delete, apply, send,
upload, drag-and-drop, and any button whose label implies a state change on the server.

Opening a "New order" dialog to document its fields is reading. Pressing its Save button is not.
If understanding a screen genuinely requires a write, **stop and ask the operator**.

---

## Step 0 — configuration, and the map itself on a first run

The skill needs to know where the map lives, which environment to browse, how to authenticate
and where the code is. That is per-project, so it lives in a config file, never in this skill.

1. **Find the config.** `map.config.yml`, normally in the map directory. Search up from the
   working directory and then across the repository — do not assume a path.
2. **If there is no config**, run the ten-question setup interview in `references/config.md` —
   all of it in one message — write the file, and confirm it with the operator before browsing
   anything. The README promises the user that exact list, so ask it in that order.
3. **If there is no map yet**, create it before documenting any screen:
   `<map_dir>/product-map.md` from `references/templates/product-map.md`, plus empty `pages/`,
   `entities/` and `functions/` directories. Fill what is already knowable — product purpose,
   roles, navigation — from the code, and leave the URL table to be filled screen by screen.
   A page file with no map to hang on is an orphan.
4. **Read the config every run** — do not cache values from a previous session. Two fields shape
   the output and are easy to forget: `output_language` (the language of the map's prose; UI
   labels always stay in the product's own language, quoted) and `auth.role` (the role the
   walkthrough saw, recorded in every page file, because it bounds everything observed).

Never invent credentials, never paste secrets into the config or into any map file: the config
stores the **path to an env file and the variable names**, nothing else.

---

## Step 1 — reconcile with the map

Open the map's main file (`<map_dir>/product-map.md`) and find the URL in the URL table.

Record: the canonical screen name, its section number, what the map already claims about it,
and the target filename in latin characters (`Orders.md`, `Order-Card.md`, `Company-Profile.md`).

- Screen missing from the URL table → tell the operator; add it or proceed and add it at Step 6.
- `pages/<Name>.md` already exists → extend and correct it, never silently overwrite. Keep
  findings that are still true, mark corrected ones.

---

## Step 2 — walk the UI, read only

Goal: the **factual structure** of the screen — headings, tabs, table columns, buttons, filters,
empty states, dialogs — plus screenshots.

Harness lives in `assets/playwright/`. Copy it once into the project (path from config
`walkthrough.dir`, default `product-map-walkthrough/`), then:

```bash
# first run only
bash <walkthrough.dir>/setup.sh

# authenticate once — headed browser, works with SSO, 2FA, captcha;
# saves a storage state, so later runs need no credentials
bash <walkthrough.dir>/run.sh --auth

# document a screen
bash <walkthrough.dir>/run.sh --target /orders --tag orders

# add when the screen's substance is in dialogs, or below the first page of a list
bash <walkthrough.dir>/run.sh --target /orders --dialogs --paginate
```

`run.sh` finds the config, reads credentials out of the env file by name, refuses production
unless it is named in the command, and writes artefacts to an absolute path. It never guesses.
Details and knobs: `assets/playwright/README.md`.

**Read `<screenshot_dir>/<tag>.json`, not the console output.** Each snapshot writes a PNG and a
JSON file holding the requested and final URL, a `redirected` flag, headings, tabs, columns,
buttons, links with their hrefs, input names, empty-state text, row count, console errors and
failed requests. Three of those fields carry findings that are easy to miss:

- `redirected: true` — the URL you asked for is not the URL you documented. Record where it went
  and why before writing anything about the screen.
- `failedRequests` / `consoleErrors` — a screen whose API answers 403 or 500 renders as an empty
  list. Without this it goes into the map as "no data". These belong in the page file, and a
  reproducible one belongs in the tracker.
- A `WARNING` about tabs that were read but not clickable means tab contents were **not**
  captured. Extend the selectors or document only what you actually saw.

If the walkthrough cannot run at all (no test environment, no credentials, product not on the
web), say so in the page file under **Status** and build from code alone — do not present
code-derived structure as UI-confirmed.

**Redirect, 403 or an empty screen is data, not a failure.** Record "not available to the
demo account (role X)" and fill the structure in from code at Step 3. Never infer screen
content from its name.

---

## Step 3 — read the code

Refresh the local checkouts first — a stale clone produces confident, wrong statements:

```bash
git -C <code.frontend> pull --ff-only && git -C <code.frontend> log -1 --format='%h %ad'
```

Record the commit hash in the page file. A map entry without a commit cannot be re-verified.

What to extract, by stack-specific recipe in `references/code-recon.md`:

- **Route → component.** Start from the routing definition, not from a filename guess.
- **Component** — services it injects, conditional rendering, role checks, filter parameters.
- **Template** — tables, tabs, links to other screens (these become "Related pages").
- **Data layer** — every HTTP call the screen makes → the **API** section.
- **Models / types / schemas** → the **Entities** section, or a file under `entities/`.
- **Localization files** → exact UI labels. Copy them; never translate or invent a label.
- **Backend** — if an endpoint is not visible in the client, grep the server repo for the path.

Search the whole app tree, not just the screens folder: auth, layout, admin areas and
feature modules outside the main routing carry screens too.

---

## Step 4 — reconcile with the documentation

The walkthrough and the code give **what works**. The documentation gives **what was intended**
and **what the customer was promised** — and, by the difference, the product's gaps.
This step is not optional: skip it and you have a described screen but an invisible backlog.

Where to look and how, per source type: `references/doc-sources.md`.

| Source | What you take from it |
|--------|----------------------|
| Knowledge base / spec space | Intent, business context, mockups, undelivered ideas |
| Issue tracker | What was filed, what shipped, and the **comments** — where scope quietly changed |
| User manuals | What the customer was told, in the customer's words |
| Support archive | What customers actually get stuck on, if this screen is a known pain point |

What to do with each finding:

- **Implementation differs from the issue it shipped under** → section
  "Divergence from issue \<KEY\>" in the page file: what the issue says, what the code does.
- **Specified but absent**, or **built differently than written** → the map's **Gaps** section,
  with the source and the issue key.
- **A manual tells the customer something untrue** → not a gap, a defect: file it and link it.
- **Built but documented nowhere** → add it to the map, and close the backlog item if one exists.

**Unfinished implementation** — a stub, a mode with no form, a field with no control, an empty
reference table — is not automatically a defect. Confirm with the owner before filing it, and
record a confirmed "intended" in the page file so it stops resurfacing.

---

## Step 5 — write the page file

Fill `references/templates/page.md` into `<map_dir>/pages/<Name>.md`.
Entities go to `entities/`, cross-cutting mechanisms to `functions/`, from the same templates.

Rules:

- **Purpose** is written for whoever uses the screen, in their language. APIs and component
  paths belong in their own sections, not in the first paragraph.
- **Fact and guess are visually separated.** Anything not seen in the UI or read in the code is
  marked `> assumed, needs verification`. Guessing is prohibited; an honest gap beats a
  plausible sentence.
- **Labels come from the localization files**, quoted exactly, with the language noted.
- **Header carries provenance**: environment browsed, role used, date, commit hash, screenshot paths.
- **Screenshot paths are written relative to the repository root** and checked to exist. A path
  that only worked in the shell that produced it is the most common rot in a map.
- **Errors seen during the walkthrough** — failed requests, console errors — go into the page
  file even when the screen looked fine. They are findings, not noise.
- Link a `functions/` or `entities/` file only if it exists; otherwise name the mechanism in plain
  text and add it to the map's cross-cutting table as "to be written".

---

## Step 6 — wire up the links

1. **Page → map**: link to the map section in the page header.
2. **Map → page**: a `> Detail: [pages/<Name>.md](pages/<Name>.md)` line under the section, not duplicated.
3. **Map index**: add or update the row in the map's page index table — file, URL, status, date.
   This table is the only place the coverage of the map is visible; keeping it current is part of the job.
4. **Page ↔ page**: outgoing links and incoming ones. When a new page appears, update the pages
   that link to it.
5. **Page ↔ function / entity**: both directions.

---

## Step 7 — report

Short, to the operator:

- file created or updated, and what changed if it existed;
- what was confirmed in the UI, what came from code, what came from documents, what is still open;
- divergences found and new entries in "Gaps";
- what the next run should cover.

---

## Working rules

- **One URL per session.** No parallel agents across screens: context spend grows faster than value,
  and cross-screen links get written from memory instead of from files.
- **Never write to the product.** When in doubt, ask instead of clicking.
- **The map is a repository artifact.** Commit it with the code; a map in a wiki rots like the wiki.
