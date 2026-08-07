# Configuration

Everything project-specific lives in one file so the skill itself stays portable.
Location: `<map_dir>/map.config.yml` — `run.sh` finds it by walking up from the working
directory and then searching the repository. Commit it. It holds no secrets: only paths,
URLs and the *names* of environment variables.

**Paths are relative to the repository root** (or, outside a repository, to the config file).
The same config then works from any working directory.

The schema is deliberately one level deep — the runner's YAML reader covers exactly this shape,
so nothing in the file is silently ignored. Do not add nested blocks or lists beyond `viewport`.

## Schema

```yaml
map_dir: docs/product-map        # where the map lives
output_language: en              # language of the map's prose; labels stay in the product's own

environments:
  staging: https://staging.example.com
  production: https://app.example.com
  default: staging               # production still requires an explicit --env production

auth:
  login_path: /auth/login
  # optional CSS selectors; the harness has sensible fallbacks
  user_selector: 'input[type=email], input[name=email], input[formcontrolname=username]'
  pass_selector: 'input[type=password], input[name=password]'
  submit_selector: 'button[type=submit]'
  # something visible only after login — required when the login page has no distinct path
  success_selector: ''
  env_file: .env.local           # path to a gitignored env file, never the values
  user_var: APP_USER
  pass_var: APP_PASSWORD
  manual_only: false             # true for SSO / 2FA / captcha — skip scripted login
  role: admin                    # the demo account's role; recorded in every page file

walkthrough:
  dir: product-map-walkthrough
  screenshot_dir: product-map-walkthrough/screenshots
  traverse_tabs: true
  settle_ms: 2500
  viewport: [1600, 1000]
  hide_selector: ''            # chrome left out of the frames, e.g. 'app-sidebar, .cookie-banner'

code:
  frontend: ../frontend          # local checkout, not a remote API
  backend: ../backend            # optional
  stack: angular                 # angular | react | next | vue | nuxt | rails | django | other
  i18n: src/assets/i18n/en.json  # source of truth for UI labels
  i18n_language: en

docs:
  knowledge_base: confluence:PRODUCT   # type:identifier, or none
  tracker: jira:WEB                    # type:identifier, or none
  manuals: docs/user-manuals           # path or URL, or none
  support: none                        # path to a support archive, or none
  how: 'MCP server `atlassian`; tracker via its REST API'
```

Values under `code:` and `docs:` are read by the agent, not by the runner. Everything under
`environments:`, `auth:` and `walkthrough:` drives `run.sh`.

## Setup interview

Ask all ten in one message, offer the defaults, write the file, show it back for confirmation.
**Do not browse anything before the config is confirmed.** This is the same list the README
promises the user, in the same order — keep them in step if you change either.

1. **Where should the map live?** (default `docs/product-map`)
2. **Which environment may I browse, and what is its base URL?** Confirm explicitly whether
   production is off limits. Default: staging only.
3. **How do I log in** — scripted with credentials, or one manual headed login saved as a session?
   If the product uses SSO, 2FA or a captcha, choose manual: it is faster and it always works.
4. **If scripted: which env file holds the credentials, under which variable names?**
   (defaults `.env.local`, `APP_USER`, `APP_PASSWORD`) The config stores the path and the names,
   never the values.
5. **Which role will the account have?** It bounds everything the walkthrough can see, so it is
   recorded in every page file.
6. **Where are the local checkouts of the frontend and backend?** They must be local clones;
   reading code through a hosted API is a fallback for a missing file, not a working mode.
7. **Which stack?** Determines the route→component recipe in `code-recon.md`.
8. **Where are the UI labels, and in which language?** Quoted from there verbatim.
9. **Which written sources exist** — knowledge base, tracker, user manuals, support archive —
   and how does the agent reach each one?
10. **Which language should the map be written in?** (prose only; labels stay in the product's own)

An answer the operator does not have is not a blocker: record the source as `none`, note what is
missing, and move on. The config is an ordinary file and can be edited later.

## Rules

- No secrets in `map.config.yml`, in page files, or in committed screenshots.
- The env file is **parsed, not executed**: only the two named variables are read out of it.
- If a credential variable is empty and no saved session exists, the runner stops. It never
  falls through to an anonymous session — an anonymous session renders a login page that reads
  like "access restricted for this role", and that lie ends up in the map.
- Add to `.gitignore`: the storage state (`.auth/`), and the screenshot directory unless the
  environment holds only synthetic data. `run.sh` warns when the screenshot directory is not ignored.
- Re-read the config on every run. Environments and stands move.
