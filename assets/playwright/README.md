# Walkthrough harness

A read-only Playwright setup for documenting one screen at a time. Copy this folder into the
product's repository (default `product-map-walkthrough/`) — the skill itself stays untouched, so
it can be updated independently.

```bash
bash setup.sh                                    # @playwright/test + chromium, non-destructive .gitignore
bash run.sh --auth                               # headed login, saves the session
bash run.sh --target /orders --tag orders        # walk one screen
bash run.sh --target /orders --dialogs           # also open and close read-only dialogs
bash run.sh --target /orders --paginate          # also snapshot the second page of a list
bash run.sh --target /orders --hide 'app-sidebar' # leave the nav rail out of the frames
bash run.sh --target /orders --env production    # only when the operator asks for it
```

Requires bash. On Windows use WSL or Git Bash; the TypeScript specs themselves are portable, so
`npx playwright test` works directly from PowerShell if you export the `MAP_*` variables yourself.

## Configuration

`run.sh` finds `map.config.yml` by walking up from the working directory, then by searching the
repository. Paths inside it resolve against the **repository root**, so the same config works from
any directory. Pass `--config <path>` to override.

## Output

For each snapshot, into the screenshot directory:

- `<tag>.png` — full-page screenshot
- `<tag>.json` — requested URL, final URL, `redirected` flag, title, headings, tabs, table
  columns, visible buttons, links with hrefs, input names, empty-state text, row count,
  **console errors** and **failed requests** (any response ≥ 400)

Read the JSON, not the console. The three fields that carry findings rather than structure are
`redirected`, `failedRequests` and `consoleErrors`: a screen whose API answers 403 renders as an
empty list, and without them the map records "no data" while the defect stays invisible.

Before each full-page shot the page is scrolled to the top and every sticky or fixed element is
made static, so a floating header does not print across the middle of the image. `--hide` (or
`walkthrough.hide_selector`) removes product chrome — a nav rail, a cookie banner, a support
widget — from the frame. Both are visual, applied after the DOM is read and reverted immediately
after the shot, and both are skipped while a dialog is open, since a dialog is fixed on purpose.

## Storyboard frames

The storyboard wants one frame per visually distinct state, filed per screen. Point the output at
the storyboard folder and give each state its own tag:

```bash
MAP_SCREENSHOT_DIR=docs/product-map/storyboard/assets/orders \
  bash run.sh --target /orders --tag list --no-tabs --hide 'app-sidebar'
```

The `<tag>.json` beside each frame is that frame's capture record. `references/storyboard.md` in
the skill has the coverage rules and the validator.

## Tabs

Tabs are traversed automatically. Candidates are found by `[role=tab]` first, then by common
class-based patterns. When labels are read but nothing is clickable, the run prints a
`WARNING` and **does not** traverse — silence would let the agent record tab contents it never
saw. Extend `tabHandles()` in your copy for products with unusual tab widgets.
Disable with `--no-tabs` or `traverse_tabs: false`.

## Dialogs and pagination

Both are opt-in, because both click things.

`--dialogs` clicks only buttons whose label starts with an opening verb (`add`, `new`, `create`,
`filter`, `settings`, `columns`, `details`, `info`, `edit`, `view`, `configure`, `import`),
screenshots whatever dialog appears, then closes it with Cancel/Close or Escape. Labels implying
a write are never clicked, in any mode, and a native `confirm()` is always dismissed, never
accepted. Check the button labels of your product before using it: if "Add" creates a row
instead of opening a form, leave the flag off.

`--paginate` clicks a next-page control once and snapshots the result.

## Authentication

`run.sh --auth` opens a visible browser. If credentials are present it fills them in; otherwise
it waits up to ten minutes while you log in by hand — which is what makes SSO, one-time codes and
captchas a non-issue. The session is written to `.auth/state.json` and reused by every later run,
so routine runs need no credentials in the environment at all.

For products that log in without changing the URL, set `auth.success_selector` — something
visible only after login. Without a distinct login path and without that selector, `--auth`
stops and says so rather than saving a session that is not one.

When a saved session expires, the walkthrough **fails loudly** instead of screenshotting the
login page. That failure mode matters: a silently anonymous session produces a page that reads
like "this role has no access", and that lie is hard to catch once it is in the map.

## Safety

- No submit, save, delete, apply, send, upload, drag-and-drop.
- Production requires `--env production` on the command line. A config default is not consent.
- The env file is **parsed, not sourced**: only the two named variables are read, nothing in the
  file is executed, and no other secret from it reaches the browser process.
- `run.sh` warns when the screenshot directory is not gitignored. Screenshots of a live product
  hold customer data.

## Environment variables

`run.sh` fills these from `map.config.yml`; set them directly to override.

| Variable | Meaning |
|----------|---------|
| `MAP_CONFIG` | Config path, if you do not want it discovered |
| `MAP_BASE_URL` | Environment being browsed — required |
| `MAP_TARGET`, `MAP_TAG` | Screen path and artefact prefix |
| `MAP_LOGIN_PATH` | Login route, default `/auth/login` |
| `MAP_ENV_FILE`, `MAP_USER_VAR`, `MAP_PASS_VAR` | Where credentials come from, by name |
| `MAP_STORAGE_STATE` | Saved session, default `.auth/state.json` |
| `MAP_SCREENSHOT_DIR` | Resolved to an absolute path before the run |
| `MAP_USER_SELECTOR`, `MAP_PASS_SELECTOR`, `MAP_SUBMIT_SELECTOR`, `MAP_SUCCESS_SELECTOR` | Login selectors |
| `MAP_TRAVERSE_TABS`, `MAP_DIALOGS`, `MAP_PAGINATE` | `0`/`1` switches for the three walk modes |
| `MAP_HIDE_SELECTOR` | CSS selector for chrome hidden while the frame is taken |
| `MAP_SETTLE_MS` | Wait after load before reading, default 2500 |
| `MAP_HEADED` | `1` shows the browser |
| `MAP_VIEWPORT` | `1920x1080` or `[1920, 1080]` |
| `PLAYWRIGHT_VERSION` | Pin used by `setup.sh`, default 1.62.1 |

## Adapting it

The default selectors cover most component libraries. When a product uses something unusual —
custom tab widgets, virtualised tables, canvas-rendered grids — edit `explore-page.spec.ts` in
your copy rather than the skill's. Keep the rule that every locator is a read.
