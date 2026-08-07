# product-map-page

An agent skill that builds and maintains a **product map**: a folder of markdown files in your
repository that says what your product does *today*.

One run documents one screen. Run it repeatedly and the map assembles itself.

## What a product map is

One set of documents recording what the product can do **right now**: which screens exist, what
a person does on each of them, what data the product holds, what is built and what is still only
discussed.

It is written from what runs, not from what was planned. The agent walks the live interface,
reads the source code, and only then looks at the written material — knowledge base and tracker
for intent, user manuals for what the customer was promised. Where a document disagrees with the
product, the product goes into the map and the disagreement is recorded separately.

Put plainly: it is the answer to "how does this actually work with us now?", which otherwise gets
reassembled every time out of people, chat history and stale specifications.

## Why bother

**Specifications rot, a map does not.** Requirements are written before the build and rarely
revised. Six months later the document says one thing and the product does another. A map derived
from what runs can carry decisions.

**A new person — or a new agent — gets context in hours, not weeks.** An engineer, an analyst or
a coding assistant reads one folder instead of reverse-engineering the app and interviewing the
team. Feeding the map to an agent before a task is the cheapest context you will ever buy.

**Absence becomes visible.** Once everything present is written in one place, the holes surface on
their own: a setting that cannot be saved, a field with no hint, a screen everyone assumed
existed. The map keeps a **Gaps** section for exactly this, linked to tracker issues.

**Less duplicate work.** Before commissioning a feature you can see whether it already exists. And
the reverse: reconciling documents against code surfaces defects that testing misses, because the
interface looks fine while the request never reaches the server or the device.

**Requirements get written faster and land better.** A new task attaches to a known screen with a
known API and known constraints, referenced by file rather than by memory.

## What is in a map

| Part | What is inside |
|------|----------------|
| **Main file** | What the product is for, who sees which sections, the menu, every screen address with a short description, the list of known gaps and the backlog |
| **Screens** | One file per screen: what it is for, what is on it, filters, buttons, tabs, which data is shown and where it comes from |
| **Entities** | The objects the product operates on, and their fields |
| **Cross-cutting functions** | Mechanisms that live across the product rather than on one screen: access control, notifications, exports, auth guards |
| **Storyboards** | One HTML page per screen: full-page screenshots of the live interface on the left, notes per state on the right |
| **Links** | References between all files in both directions — from the map into a screen and back |

```
<map_dir>/
  product-map.md          # purpose, roles, navigation, URL table, gaps, page index
  map.config.yml          # per-project configuration, no secrets
  pages/
    Orders.md
    Order-Card.md
  entities/
    Order.md
  functions/
    Access-Control.md
  storyboard/
    index.html            # every screen, plus what deliberately has no frame
    orders.html           # frames left, notes right
    assets/orders/*.png
```

## How it is assembled

The agent works one screen per session, in this order.

1. **Looks at the screen the way a user does.** Opens the test environment, goes through the tabs,
   captures the structure and screenshots. Changes nothing and saves nothing — read only, so live
   data is never touched.
2. **Reads the code.** What the screen asks the server for, which fields the data has, who sees
   what. Labels are taken from the localisation files, never invented.
3. **Reconciles with the documentation.** Knowledge base and tracker give intent and business
   context; user manuals give what the customer was told. This is also where the gap list comes
   from: described but not built, and built differently than described.
4. **Writes it up in a fixed shape** — purpose in plain language, contents, data, access, links to
   other screens.
5. **Separates fact from guess.** Anything not confirmed by the interface or the code is marked as
   needing verification. Inventing is prohibited.
6. **Builds the storyboard.** One frame per visually distinct state — every tab, every mode of a
   form, every wizard step, the empty state — and notes written from the opened screenshot rather
   than from its file name. This is the step that catches what reading code cannot: a typo in a
   label, a field that exists in one mode and not in its neighbour, a form nobody had opened for
   a year.

**The rule that makes it worth trusting:** the senior source is the code, confirmed by a walk
through the live interface. Design documents were written before the build and never revised,
manuals lag the product, issues describe intent rather than outcome. So documents are context and
a source of discrepancies — never grounds for writing "the feature works like this".

## What it turns out to be good for

Beyond onboarding and requirements, teams use a map for:

- **Auditing what is documented against what is in the code** — walking every screen and comparing
  the list of server calls with the descriptions usually surfaces endpoints and modes that appear
  in no document at all.
- **Making sense of support traffic** — support conversations and tickets read against a map stop
  being anecdotes and become a ranked list of where the product, not the manual, needs fixing.
- **Taking one screen down to the protocol** — mapping "setting in the interface → command sent to
  the device → parameters" turns a vague form into a list of concrete defects and confirmed
  intentional behaviours.
- **Refreshing after a release** — closed issues plus their comments, diffed against the code, so
  the map records the implementation and, separately, where it diverged from the specification.
- **Writing requirements for a neighbouring project** — a map of the adjacent product answers "does
  this screen exist?" in one pass, before development rather than after.
- **Describing your own work outward** — the map is ready-made evidence of scope, authorship and
  depth of a product.

## Install

Copy this folder into your agent's skills directory:

```bash
# Claude Code (project-level)
cp -R product-map-page .claude/skills/

# Cursor
cp -R product-map-page .cursor/skills/

# both, without duplicating the source
ln -s ../../.claude/skills/product-map-page .cursor/skills/product-map-page
```

Then run it by name — `/product-map-page` — with the URL of a screen.

The skill ships with `disable-model-invocation: true`: it will not fire on its own. That is
deliberate. It drives a browser against a running product and writes files; you want it started by
a human, one screen at a time. Remove the line from the frontmatter if you disagree.

Requires bash, node and git. On Windows, run the harness under WSL or Git Bash.

## Setup wizard — what the agent asks on the first run

The first time the skill runs in a repository there is no configuration and usually no map. It
asks the questions below in one message, writes `<map_dir>/map.config.yml`, shows it back for
confirmation, and only then opens a browser. **Nothing is browsed before the config is confirmed.**

Have these ready and the wizard takes two minutes.

| # | Question | Default | Why it is asked |
|---|----------|---------|-----------------|
| 1 | Where should the map live? | `docs/product-map` | Everything else is written relative to this, and the map belongs in the repository rather than in a wiki |
| 2 | Which environment may be browsed, and what is its base URL? Is production off limits? | staging only | The walkthrough is read-only, but a test environment is still the right target. Production later requires naming it explicitly in the command |
| 3 | How is the login done — scripted with credentials, or one manual login saved as a session? | manual, if the product uses SSO, 2FA or a captcha | A manual headed login once beats fighting selectors forever; the saved session is reused by every later run |
| 4 | If scripted: which env file holds the credentials, and under which variable names? | `.env.local`, `APP_USER`, `APP_PASSWORD` | The config stores the **path and the names**, never the values. The file is parsed, not executed |
| 5 | Which role will that account have? | — | It bounds everything the walkthrough can possibly see, so it is recorded in every screen file |
| 6 | Where are the local checkouts of the frontend and, if there is one, the backend? | `../frontend`, `../backend` | The code is the senior source. Reading it through a hosted API is a fallback for a missing file, not a working mode |
| 7 | Which stack is the frontend? | — | Chooses the route → component → API recipe: Angular, React, Next, Vue, Nuxt, or a server-rendered framework |
| 8 | Where are the interface labels, and in which language? | `src/assets/i18n/en.json` | Labels are quoted from there verbatim; a paraphrased label makes the map unsearchable for the people who see the screen |
| 9 | Which written sources exist — knowledge base, issue tracker, user manuals, support archive — and how does the agent reach each one? | — | Determines what the reconciliation step can check, and therefore how complete the gap list will be |
| 10 | Which language should the map be written in? | English | Prose follows this; interface labels always stay in the product's own language |

If the map does not exist yet, the agent also creates `product-map.md` and the empty `pages/`,
`entities/` and `functions/` folders from the templates, filling in what is already knowable —
product purpose, roles, navigation — and leaving the screen table to fill up run by run.

Answers you do not have yet are not blockers: say so, and the agent records the source as `none`
and notes what is missing. `map.config.yml` is a normal file — edit it later.

## First screen

```bash
cp -R <skill>/assets/playwright product-map-walkthrough   # copy the walkthrough harness
bash product-map-walkthrough/setup.sh                     # playwright + chromium
bash product-map-walkthrough/run.sh --auth                # log in once, save the session
```

Then point the skill at a screen: `/product-map-page /orders`

Start with the busiest list screen in the product. It sets the tone for the rest of the map, and
it is the one you will read most often.

## Safety

- **Read-only by construction.** The skill may navigate, switch tabs, paginate, change a date
  range, open and close dialogs, and screenshot. It may not submit, save, delete, apply, send or
  upload. Labels implying a write are never clicked, and a native `confirm()` is always dismissed.
  If understanding a screen needs a write, it stops and asks.
- **Staging by default.** Production requires `--env production` on the command line; a default
  written into the config months ago is not consent.
- **No secrets in files.** The config points at an env file and names two variables; the file is
  parsed, never executed. The session saved by `run.sh --auth` lands in a gitignored path.
- Screenshots may contain customer data. `run.sh` warns when the screenshot directory is not
  gitignored.

## Known limits

- Dialog and pagination walks are opt-in flags, not automatic — they click, so you decide.
- Tab traversal covers `[role=tab]` and common class patterns; anything more exotic prints a
  warning and is left to you rather than being silently skipped.
- The harness reads the rendered DOM. Canvas-rendered grids, virtualised lists beyond the first
  window, and content behind hover need a hand-written locator.
- Storyboard states the harness cannot reach on its own — a mode selector behind a custom widget,
  a step of a wizard — need a product-specific capture spec copied from `explore-page.spec.ts`.
  States that would require a write are not captured at all; they are listed with the reason.
- One screen per session is a working rule, not something the tooling enforces.

## Contents

| File | Purpose |
|------|---------|
| `SKILL.md` | The instruction the agent follows: seven steps, source hierarchy, read-only rule |
| `references/config.md` | Configuration schema and the setup interview |
| `references/code-recon.md` | Route → component → API recipes per stack |
| `references/doc-sources.md` | Reconciling with knowledge base, tracker, manuals, support; how gaps are filed |
| `references/storyboard.md` | Capturing frames, which states must exist, how the notes are written and checked |
| `references/validate-storyboard.py` | Pre-delivery check of the storyboard folder: markup, images, links, orphaned and duplicate frames, boilerplate notes |
| `references/templates/` | Skeletons for `product-map.md`, `pages/`, `entities/`, `functions/`, and the storyboard pages |
| `assets/playwright/` | The read-only walkthrough harness: setup, auth, explore |

## Maintenance

After a release, take the closed issues **with their comments**, diff them against the code and
update the affected screens. What goes into the map is the **implementation, not the
specification** — the two differ more often than anyone expects, and that difference is worth
recording on its own.

Re-read the **Gaps** section before planning: some entries close themselves when a neighbouring
feature ships differently than it was written.

If the map is mirrored into a shared team repository, keep the working copy next to the product
and sync the mirror through a normal branch and merge request.

## Author

Yuriy Egorov — [github.com/fzrx-ego](https://github.com/fzrx-ego)

## Licence

MIT. Take it, strip what does not apply, keep the source hierarchy — it is the part that makes the
map worth trusting.
