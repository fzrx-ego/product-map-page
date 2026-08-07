# <Product> — product map

**Updated:** YYYY-MM-DD
**Source of truth:** code at commit `<hash>`, confirmed by a read-only walkthrough of `<environment>`.
Documents listed at the bottom are context and a source of divergences, not evidence of behaviour.

---

## What this product is

<Two or three sentences: who uses it, for what, in place of what.>

## Roles and access

| Role | Sees | Cannot |
|------|------|--------|

## Navigation

<The menu as it renders, per role. This is the fastest orientation anyone gets, so keep it exact.>

## URL table

### 0. System and auth

| URL | Screen | Notes |
|-----|--------|-------|

> Detail: [pages/Auth.md](pages/Auth.md)

### 1. <Section>

| URL | Screen | Notes |
|-----|--------|-------|

> Detail: [pages/<Name>.md](pages/<Name>.md)

<...one numbered section per functional area. Include areas that exist in code but not in the
menu: admin panels, white-label configuration, public machine-to-machine APIs, modules mounted
outside the main router. They are the ones nobody remembers.>

---

## Entities

| Entity | File | Used by |
|--------|------|---------|

## Cross-cutting functions

| Function | File | What it is |
|----------|------|-----------|
| Access control | `functions/Access-Control.md` | Guards, roles, record scope |
| <...> | — *(to be written)* | <one line> |

---

## Gaps

Grouped by where the claim came from. Each entry: what is missing or different, what the code
actually does, and the issue tracking it.

### From the user manuals

### From the knowledge base

### From the tracker

### From local specifications

---

## Page index

| # | File | URL | Status |
|---|------|-----|--------|
| 1 | `pages/<Name>.md` | `/<path>` | code + walkthrough + docs (YYYY-MM-DD) |

<This table is the map's coverage. Update it on every run — it is the only place where "what is
not documented yet" is visible.>

---

## Sources

| Source | Used for |
|--------|----------|
| `<frontend repo>` | Structure, API calls, models, labels |
| `<backend repo>` | Endpoints not visible in the client |
| `<knowledge base>` | Intent and business context |
| `<tracker>` | What shipped, and where scope changed |
| `<manuals>` | What the customer was promised |
