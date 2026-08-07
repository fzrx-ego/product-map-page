# Reading the code for one screen

The goal is narrow: for a single URL, find the component that renders it, then extract structure,
data calls, models, access rules and exact labels. Everything here is `grep` + `read` on a local
checkout. Reading through a hosted git API is a fallback for a missing file, never the default.

## 0. Freshness first

```bash
git -C "$FRONTEND" pull --ff-only
git -C "$FRONTEND" log -1 --format='%h %ad %s'
```

Write that hash into the page file. Without it, nobody can tell later whether a discrepancy is a
product change or a stale clone — and a stale clone makes the agent confidently describe a screen
that no longer exists.

## 1. Route → component

Never guess the file from the URL segment. Start from the routing definition.

**Angular**

```bash
grep -rn "'orders'" "$FRONTEND/src" --include='*routing*.ts' --include='*.module.ts'
```
Follow `loadChildren` into the feature module, then its own routing file, then `component:`.
Child routes give the screen's tabs. `canActivate` guards give access rules.

**React Router / TanStack Router**

```bash
grep -rn "path=.*orders\|path: *'/orders" "$FRONTEND/src"
```
Follow `element` / `component` / `lazy`. Check the loader or route-level data fetch.

**Next.js**

File-system routed: `app/orders/page.tsx` or `pages/orders.tsx`. Look for `layout.tsx`,
`loading.tsx`, `middleware.ts` (this is where auth redirects live), and server actions —
they are data mutations invisible to a network-tab reading.

**Vue Router / Nuxt**

`grep -rn "path: *'/orders'" src/router` — or, in Nuxt, `pages/orders.vue` by convention.

**Server-rendered (Rails, Django, Laravel)**

Start from the route table (`config/routes.rb`, `urls.py`, `routes/web.php`) → controller action
→ template. The template *is* the structure; there is no client model layer to read.

## 2. What to extract

| Target | Where | Goes into |
|--------|-------|-----------|
| Screen state machine — loading, empty, error, no-permission | Component conditionals | "Screen states" |
| Tabs, table columns, row actions | Template | "Contents" |
| Filters and their parameters | Component + query-param handling | "Filters" |
| Every HTTP call | Data service / hooks / loaders | "API" table |
| Field names, types, optionality | Models, types, schemas, OpenAPI | "Entities" |
| Role checks, guards, feature flags | Guards, `hasRole`-style helpers, conditional rendering | "Access" |
| Exact button and column labels | Locale files | Everywhere — quoted verbatim |
| Links to other screens | `routerLink`, `<Link>`, `href` | "Related pages" |

## 3. API section

For each call record: method, path, when it fires, and what the screen does with the answer.
Query parameters matter — they encode the filtering and paging contract:

```bash
grep -rn "http\.\(get\|post\|put\|patch\|delete\)\|fetch(\|axios\." "$FRONTEND/src/<feature>"
```

If an endpoint appears in no client code but the UI clearly uses it, grep the backend for the
path. If the product has an OpenAPI or GraphQL schema, read it — but verify against the client:
schemas describe what the server offers, not what the screen calls.

A live API client (an MCP server, a REST console, an authenticated `curl` against staging) is a
legitimate **read-only** confirmation of shapes and enums. Use `GET` only.

## 4. Labels

Copy labels from the locale file, quoted, with the language noted. Never translate a label into
the map's prose language and never write from memory — a wrong label makes the map unsearchable
for the people who actually see the screen.

```bash
grep -n "orders" "$FRONTEND/src/assets/i18n/en.json"
```

If keys are resolved dynamically, note the key pattern rather than inventing the string.

## 5. Search the whole tree

Screens hide outside the obvious folder: authentication flows, layout shells, admin-only areas,
white-label configuration, feature modules mounted outside the main router, embedded third-party
panels. Before declaring a screen absent, grep the whole `src`.

## 6. When code and UI disagree

The UI wins as evidence that something exists; the code wins as explanation of how it works. If
the walkthrough shows a control that the code seems not to render, the checkout is stale, the
environment runs a different build, or a feature flag is on. Resolve it before writing — an
unresolved contradiction in a map is worse than an admitted gap.
