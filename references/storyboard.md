# Storyboard — the visual half of a screen file

A page file says what a screen does. A **storyboard** shows it: **left** — full-page screenshots of
the live interface, **right** — notes explaining each state. One HTML page per screen, opened from
disk, committed next to the map.

It is not decoration. A frame is the only artefact in the map that cannot be written from memory:
it carries the labels as they really are, the fields that really exist, and the states nobody
remembered to describe. Half the defects a map surfaces are found while writing the notes for a
frame, not while reading the code.

For an as-is map the left column is **screenshots**. Hand-drawn HTML mocks belong in
future-facing specs, never in a map of what runs today.

## Where it lives

```
<map_dir>/storyboard/
  storyboard.css          # shared shell, no external resources: no CDN, no web fonts
  index.html              # every screen, plus what deliberately has no frame
  <slug>.html             # one screen (orders.html, order-card.html)
  assets/<slug>/*.png     # full-page desktop frames
  assets/<slug>/*.json    # the harness's capture record, one per frame
```

Templates: `templates/storyboard.html`, `templates/storyboard-index.html`, `templates/storyboard.css`.

Mobile frames are **off** by default: they double the capture cost and the map is read on desktop.
Add them as a separate pass when someone asks.

## When

Always, alongside creating or substantially updating `pages/<Name>.md`. Without a storyboard the
screen run is not finished — including every mode in which the form changes.

---

## Capturing

The shipped harness writes one PNG plus one JSON per tag. Point it at the storyboard folder and
give each state its own tag:

```bash
MAP_SCREENSHOT_DIR=<map_dir>/storyboard/assets/orders \
  bash <walkthrough.dir>/run.sh --target /orders --tag list --no-tabs

MAP_SCREENSHOT_DIR=<map_dir>/storyboard/assets/orders \
  bash <walkthrough.dir>/run.sh --target /orders --tag list-empty --hide 'app-sidebar'
```

The `<tag>.json` sitting next to each frame **is** the capture record: requested URL, final URL,
`redirected`, failed requests, console errors. Keep it in the folder; the validator reads it.

Rules that decide whether the set is usable:

1. **Desktop viewport, fixed for the whole screen** (`walkthrough.viewport`, e.g. `[1440, 900]`).
   Frames of one screen taken at different widths cannot be compared.
2. **Collapse the product chrome.** A wide empty sidebar eats a third of every frame. Pass
   `--hide '<selector>'` or set `walkthrough.hide_selector`. Sticky and fixed elements are
   flattened automatically before the shot — otherwise a floating header prints across the middle
   of a full-page frame.
3. **All frames of one screen on one entity.** Otherwise half the set silently describes a
   different order, invoice or customer. Pick the entity once, keep its id in the tag or in a
   variable, and check the frame really opened it.
4. **Never hardcode an entity id that worked last month.** Take the first row of the list, or find
   the row by a search field; ids expire and the run then documents a 404.
5. **Wait for data, not skeletons.** If the API answers 401 or 404, stop the run instead of
   leaving empty frames in the folder — an empty frame reads as an empty state and enters the map
   as a fact. `redirected: true` or a 4xx in the sidecar JSON means the frame is about a different
   screen than you asked for; resolve that before writing a word.
6. **Read only.** No save, create, delete, send. Allowed and often necessary: switching tabs,
   selecting a mode locally, moving between steps of a form **when the step change is client-side**
   — verify in the component that the request only leaves on submit. Typing into fields to reach
   such a step is reading: nothing is sent.
7. **States that need a write are not invented.** List them under "Not captured" in the screen's
   storyboard and repeat them in `index.html`, each with the reason.

For anything the shipped harness cannot reach — a mode selector behind a custom widget, a wizard
step, a provider-specific form — copy `explore-page.spec.ts` into the walkthrough folder and add a
product-specific capture spec. Keep every locator a read.

### Re-capturing

Re-shoot a whole screen after any change to how it is captured (viewport, hidden chrome, entity
binding). Mixed sets are worse than missing ones. When a capture script grows per-state functions,
make sure each one honours the same "skip existing" switch — otherwise a full run prints
`skip existing` and quietly re-uses half of the old set.

---

## Frame coverage — completeness of states comes first

**One frame "as it opened" is not enough** when the interface changes with a mode, an entity type,
a role or an empty result. Capture a separate full-page frame for **every visually distinct
state**:

| Screen kind | States that must exist |
|-------------|------------------------|
| List | with data; empty state, when the environment can produce one; a filter applied, if it changes the columns |
| Detail card | every tab |
| Form whose shape depends on a mode | every mode — each one is its own frame |
| Sub-selector inside a mode | every option that changes the **set of fields**, not the highlight |
| Wizard | every step, times every entity type where the steps differ |
| Dialog | opened and closed without submitting |
| Role-dependent screen | one frame per role that sees a different composition, when accounts exist |
| System screens | maintenance, suspended, forbidden, not-found |

**Spend a frame where the set of fields differs, not where a button lights up.** The usual failure
is three frames of step 1, which differ only in a highlighted card, and no frame of step 2, where
one entity type loses a field entirely.

File names: `kebab-case.png` inside `assets/<slug>/` — `settings-basic.png`, `settings-advanced.png`.

---

## The notes column

Explain the screen to someone who has never opened it: who uses it, what for, what leaves for the
server or the device, how this state differs from its neighbours.

| Block | Contents |
|-------|----------|
| What this screen / state is for | Purpose in plain language: what the person does and what they leave with |
| How you get here | Address, menu item, which click or mode opened this state |
| What is on screen (full composition) | Sections and fields visible **in this state**; buttons; banners |
| How it differs | From the neighbouring states **of this same screen** |
| Gaps / observed on the frame | What is unfinished; oddities visible in the shot |
| Issue | Tracker key, if one was filed for the finding |

Tags on each block: `As-is`, the mode name, `Empty state`, `Not captured`, risk.

### Reconciling with the open frame — required

The notes are written **from the opened PNG**, not from the file name and not from the name of the
mode. Open every frame and check:

- **Labels** exactly as the interface shows them, including a typo. Do not shorten them, do not
  turn them into a slug, do not translate them into what they ought to say.
- **Composition of fields** as actually visible. Similar modes diverge: one has a tag next to the
  price, the neighbour does not; "up to three positions" turns out to be eight on the frame.
- **Disabled and empty controls** written as they are: "the eighth price/tag pair is disabled".
- **Empty state** labelled as empty — in the block heading, in a tag, and with a separate line
  saying what appears when there is data.
- **Internal codes** (`method 3`, "mode 6/7") stay out of the notes. They mean nothing to the
  reader of a map.

"How it differs" must name a concrete difference from the neighbouring state. The same sentence
repeated across blocks means the block was not written: sixteen provider forms all saying
"a different set of fields" are worth nothing.

### Markup

- **A frame caption (`visual-cap`) starts with the screen's address:** `Desktop · /items/:id/settings · Advanced`.
  The first part after the device is the address, the rest is the state inside the screen. The canvas
  joins frames to routes on that caption; without an address the join has to be maintained by hand in
  `states-manual.json` and breaks on the first re-capture.
- HTML is written as HTML: field names and paths go in `<code>`, not in markdown backticks.
- Table of contents: labels not cut mid-word, order identical to the order of blocks in the body.
- No external resources — no web fonts, no CDN. The pages are opened from disk, offline.
- Remove orphaned and byte-identical frames, and keep the folder in step with what the page shows.

---

## Checks before delivery

1. **The validator** — [validate-storyboard.py](validate-storyboard.py): markup, missing images,
   dead links and anchors, markdown backticks left in HTML, external resources, orphaned and
   duplicate frames, boilerplate "How it differs", frames captured on a redirected URL or with
   failed requests.

```bash
python3 <skill>/references/validate-storyboard.py <map_dir>/storyboard
```

2. **Render it in a browser.** Read the page with your eyes, not only the file: no horizontal
   scrollbar, no failed requests.

```js
// node this file from the walkthrough folder
const { chromium } = require('@playwright/test');
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1500, height: 1000 } });
p.on('requestfailed', r => console.log('failed:', r.url()));
await p.goto('file://<absolute path>/index.html', { waitUntil: 'networkidle' });
console.log('h-scroll:', await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2));
await b.close();
```

3. **Reconcile with the sources.** The frame outranks the document: where it disagrees with
   `pages/<Name>.md` or `product-map.md`, fix those files rather than bending the caption to match
   them. This is how a field that was removed from the code but left in the description gets found.

---

## Findings from the frames

Frames regularly surface what reading code does not: typos in labels, a hardcoded date, a
"update" heading on a create form, disabled fields, a wizard that disagrees with the main form.

1. Record it in `product-map.md` under **Findings from the walkthrough**: screen, what is visible
   on the frame, what to do about it.
2. Mark it in the storyboard block itself, on a line of its own.
3. **Unfinished implementation** — a stub wizard, a form with no control — is not filed as a defect
   until the owner confirms. A confirmed "intended this way" goes into `pages/<Name>.md` so it does
   not resurface.
4. Before filing an issue, three searches in the tracker:
   - a duplicate (`summary ~` and `description ~` on the finding's keyword);
   - a **contradicting open issue** — an old ticket asking for the opposite change turns the same
     finding into a different task;
   - an issue already closed that should have covered it — then the finding is a bug that links to
     it, not a new feature request.
5. After filing, write the key back: into the map, into the storyboard block, and into the epic's
   requirements if there is one.

---

## Links

1. `pages/<Name>.md` header carries a **Storyboard:** line pointing at `../storyboard/<slug>.html`.
2. The map's page index links the storyboard and names the states captured.
3. `index.html` lists every screen and keeps a section for what has no frame, with a reason per
   entry.
4. Storyboards link to each other where the interface is shared — a customer card pointing at the
   provider forms documented under the company profile, a per-entity transaction tab pointing at
   the global journal.

## What not to do

- Do not replace as-is frames with an HTML mock "as the front end will look".
- Do not write a caption from the file name, and do not clone one sentence across ten blocks.
- Do not leave a wide empty sidebar in every frame.
- Do not assemble one screen's set from several entities.
- Do not spend frames on states that differ only by a highlighted button, and do not skip the step
  where the set of fields changes.
- Do not publish frames with skeletons, spinners or an expired session.
- Do not stop at one frame of a form whose shape depends on a mode or on a selected provider.
