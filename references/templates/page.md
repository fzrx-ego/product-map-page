# <Screen name> — <map section>

**URL:** `<base_url><path>`
**Map section:** [product-map.md → <n>. <Section>](../product-map.md#<anchor>)
**Component:** `<path/to/component>`
**Visible to:** <roles / guards>
**Status:** <verified in UI on `<environment>` as role `<role>`, YYYY-MM-DD, commit `<hash>` | code only, no UI access>
**Screenshots:** `<path from the repository root>/<tag>_main.png`, `…/<tag>_<tab>.png`
<!-- Repository-root-relative, and verified to exist. A path that only resolved in the shell
     that produced it is the most common way a map rots. -->
<!-- If the requested URL redirected, say so here: "/orders redirects to /dashboard for this role" -->


---

## Purpose

<One or two sentences in the language of whoever uses this screen. What job it does, who opens
it, what they leave with. No API paths, no component names.>

## Screen states

<Loading, empty, error, no-permission — and what each one says. The empty state is where product
intent leaks; quote it.>

## Filters and period

<Controls, defaults, whether state survives a reload, which query parameters they map to.>

## Contents

### Table / tabs / widgets

<Columns with their source field, tabs with what each holds, row actions. Quote labels exactly,
in the product's own language, noting which locale.>

### Dialogs

<Dialogs reachable from this screen: what fields they hold, what they submit. Opened and closed
without submitting — say so.>

## API

| Method | Endpoint | Fires when | Used for |
|--------|----------|-----------|----------|

<Query parameters that encode the filtering and paging contract go under the table.>

## Entities

| Field | Type | Meaning |
|-------|------|---------|

<Or, if the object is used by several screens: `> Detail: [entities/<Name>.md](../entities/<Name>.md)`>

## Access

<Which roles see the screen, which see individual controls, which guard enforces it and where.
Scope rules — whose records this role sees — belong here; they are the most frequently
misremembered thing in any product.>

<If a cross-cutting file exists: `> Detail: [functions/Access-Control.md](../functions/Access-Control.md)`>

## Errors observed during the walkthrough

<Failed requests and console errors from the walkthrough JSON, with what the screen showed while
they happened. A list that renders empty because its API answered 403 looks like "no data" —
this section is where that stops being invisible. Link the tracker issue if one was filed.
Omit the section when the walkthrough was clean.>

## Divergences from the documentation

<Found at Step 4. For each: what the document or issue says, what the code does, which one the
map records, and the issue key if one exists. Omit the section if nothing was found — do not
leave an empty heading.>

## Assumptions

> assumed, needs verification — <statement, and what would confirm it>

<Everything not seen in the UI and not read in the code lives here, never in the sections above.>

## Related functions

## Related pages

## Incoming links

<Which screens link here, so the graph stays traversable in both directions.>
