#!/usr/bin/env bash
# Read-only walkthrough runner for the product-map-page skill.
#
#   bash run.sh --auth                            # log in once, save the session
#   bash run.sh --target /orders --tag orders     # document a screen
#   bash run.sh --target /orders --dialogs        # also open and close read-only dialogs
#   bash run.sh --target /orders --paginate       # also snapshot the second page of a list
#
# Finds map.config.yml by walking up from the current directory, then by searching the
# repository. Paths inside the config are resolved against the repository root, never against
# whatever directory the runner happened to be started from.
#
# Credentials are read out of the env file by name — the file is parsed, never executed.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${MAP_CONFIG:-}"
TARGET=""; TAG=""; MODE="explore"; ENV_NAME=""; ENV_EXPLICIT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --auth)      MODE="auth" ;;
    --target)    TARGET="${2:-}"; shift ;;
    --tag)       TAG="${2:-}"; shift ;;
    --config)    CONFIG="${2:-}"; shift ;;
    --env)       ENV_NAME="${2:-}"; ENV_EXPLICIT=1; shift ;;
    --dialogs)   export MAP_DIALOGS=1 ;;
    --paginate)  export MAP_PAGINATE=1 ;;
    --headed)    export MAP_HEADED=1 ;;
    --no-tabs)   export MAP_TRAVERSE_TABS=0 ;;
    -h|--help)   sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# ---------- config ----------------------------------------------------------
# Flat "parent: / key: value" lookups. The schema in references/config.md is deliberately
# one level deep so that this reader covers all of it — no silent misses.
yaml_get() { # yaml_get <file> <parent-or-dot> <key>  → value, or empty
  awk -v p="$2" -v k="$3" '
    p == "." {
      if ($0 ~ "^"k":") { sub("^"k":[[:space:]]*", ""); found = 1 }
    }
    p != "." {
      if ($0 ~ "^"p":") { inb = 1; next }
      if (inb && $0 ~ /^[^[:space:]#]/) { inb = 0 }
      if (inb && $0 ~ "^[[:space:]]+"k":") { sub("^[[:space:]]+"k":[[:space:]]*", ""); found = 1 }
    }
    found { sub("[[:space:]]*#.*$", ""); gsub(/["'"'"']/, ""); sub("[[:space:]]+$", ""); print; exit }
  ' "$1"
}

find_config() {
  local d hit root
  d="$(pwd)"
  while : ; do
    if [ -f "$d/map.config.yml" ]; then printf '%s' "$d/map.config.yml"; return 0; fi
    if [ -d "$d/.git" ] || [ "$d" = "/" ]; then break; fi
    d="$(dirname "$d")"
  done
  root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -z "$root" ]; then root="$(dirname "$HERE")"; fi
  hit="$(find "$root" -maxdepth 4 -name map.config.yml -not -path '*/node_modules/*' 2>/dev/null | head -1)"
  if [ -n "$hit" ]; then printf '%s' "$hit"; return 0; fi
  return 1
}

if [ -z "$CONFIG" ]; then CONFIG="$(find_config || true)"; fi

# Paths in the config are repository-root-relative, so that the same config works from any
# working directory. Without a repository, they are relative to the config file itself.
BASE_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$BASE_DIR" ] && [ -n "$CONFIG" ]; then BASE_DIR="$(cd "$(dirname "$CONFIG")" && pwd)"; fi
if [ -z "$BASE_DIR" ]; then BASE_DIR="$(dirname "$HERE")"; fi

resolve() { case "$1" in /*) printf '%s' "$1" ;; *) printf '%s/%s' "$BASE_DIR" "$1" ;; esac; }

if [ -n "$CONFIG" ] && [ -f "$CONFIG" ]; then
  echo "config:   $CONFIG"
  if [ -z "$ENV_NAME" ]; then ENV_NAME="$(yaml_get "$CONFIG" environments default)"; fi
  ENV_NAME="${ENV_NAME:-staging}"
  : "${MAP_BASE_URL:=$(yaml_get "$CONFIG" environments "$ENV_NAME")}"
  : "${MAP_LOGIN_PATH:=$(yaml_get "$CONFIG" auth login_path)}"
  : "${MAP_USER_SELECTOR:=$(yaml_get "$CONFIG" auth user_selector)}"
  : "${MAP_PASS_SELECTOR:=$(yaml_get "$CONFIG" auth pass_selector)}"
  : "${MAP_SUBMIT_SELECTOR:=$(yaml_get "$CONFIG" auth submit_selector)}"
  : "${MAP_SUCCESS_SELECTOR:=$(yaml_get "$CONFIG" auth success_selector)}"
  : "${MAP_ENV_FILE:=$(yaml_get "$CONFIG" auth env_file)}"
  : "${MAP_USER_VAR:=$(yaml_get "$CONFIG" auth user_var)}"
  : "${MAP_PASS_VAR:=$(yaml_get "$CONFIG" auth pass_var)}"
  : "${MAP_SCREENSHOT_DIR:=$(yaml_get "$CONFIG" walkthrough screenshot_dir)}"
  : "${MAP_VIEWPORT:=$(yaml_get "$CONFIG" walkthrough viewport)}"
  : "${MAP_SETTLE_MS:=$(yaml_get "$CONFIG" walkthrough settle_ms)}"
  if [ "$(yaml_get "$CONFIG" auth manual_only)" = "true" ]; then export MAP_MANUAL_AUTH=1; fi
  if [ "$(yaml_get "$CONFIG" walkthrough traverse_tabs)" = "false" ]; then export MAP_TRAVERSE_TABS=0; fi
else
  echo "config:   none found — using MAP_* environment variables"
  echo "          (expected map.config.yml in the map directory; pass --config to point at it)"
fi

: "${MAP_BASE_URL:?base URL is not set — pass --config <map.config.yml> or export MAP_BASE_URL}"
export MAP_BASE_URL
export MAP_LOGIN_PATH="${MAP_LOGIN_PATH:-/auth/login}"
for v in MAP_USER_SELECTOR MAP_PASS_SELECTOR MAP_SUBMIT_SELECTOR MAP_SUCCESS_SELECTOR MAP_VIEWPORT MAP_SETTLE_MS; do
  if [ -n "${!v:-}" ]; then export "$v"; fi
done

# ---------- environment guard -----------------------------------------------
# Production is browsed only when the operator names it in the command. A config default is
# not consent: it was written once, months ago, by someone who is not in the room now.
if [ "$ENV_NAME" = "production" ] && [ "$ENV_EXPLICIT" -eq 0 ]; then
  echo "ERROR: the config points the default environment at production." >&2
  echo "       Re-run with --env production if that is really intended." >&2
  exit 1
fi
case "$MAP_BASE_URL" in
  *localhost*|*127.0.0.1*|*staging*|*stage.*|*dev.*|*test.*|*rc.*|*uat*|*.local*) : ;;
  *) echo "warning:  '$MAP_BASE_URL' does not look like a test environment."
     echo "          The walkthrough is read-only, but confirm this is the intended target." ;;
esac

# ---------- credentials -----------------------------------------------------
# The env file is parsed, not sourced: sourcing executes whatever is in it and exports every
# other secret in the file into the browser process.
read_env_var() { # read_env_var <file> <name>
  [ -f "$1" ] || return 0
  grep -E "^[[:space:]]*(export[[:space:]]+)?$2=" "$1" | tail -1 \
    | sed -E "s/^[[:space:]]*(export[[:space:]]+)?$2=//" \
    | sed -E 's/^"(.*)"$/\1/; s/^'"'"'(.*)'"'"'$/\1/'
}

USER_VAR="${MAP_USER_VAR:-APP_USER}"
PASS_VAR="${MAP_PASS_VAR:-APP_PASSWORD}"
export MAP_USER="${!USER_VAR:-}"
export MAP_PASS="${!PASS_VAR:-}"

if [ -n "${MAP_ENV_FILE:-}" ]; then
  ENV_PATH="$(resolve "$MAP_ENV_FILE")"
  if [ -f "$ENV_PATH" ]; then
    echo "env file: $ENV_PATH"
    [ -n "$MAP_USER" ] || MAP_USER="$(read_env_var "$ENV_PATH" "$USER_VAR")"
    [ -n "$MAP_PASS" ] || MAP_PASS="$(read_env_var "$ENV_PATH" "$PASS_VAR")"
    export MAP_USER MAP_PASS
  else
    echo "warning:  env file not found: $ENV_PATH (config value: $MAP_ENV_FILE)" >&2
  fi
fi

export MAP_STORAGE_STATE="${MAP_STORAGE_STATE:-$HERE/.auth/state.json}"

SHOT_DIR="$(resolve "${MAP_SCREENSHOT_DIR:-$HERE/screenshots}")"
mkdir -p "$SHOT_DIR"
MAP_SCREENSHOT_DIR="$(cd "$SHOT_DIR" && pwd)"
export MAP_SCREENSHOT_DIR

# Screenshots of a live product hold customer data. Say so before, not after, the commit.
if git -C "$BASE_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  if ! git -C "$BASE_DIR" check-ignore -q "$MAP_SCREENSHOT_DIR" 2>/dev/null; then
    echo "warning:  $MAP_SCREENSHOT_DIR is not gitignored — screenshots may hold customer data." >&2
  fi
fi

# A missing session plus missing credentials means an anonymous browser, which renders a login
# page that reads exactly like "this role has no access". Stop instead of poisoning the map.
# `--auth` is exempt: it is the way out of that state, by hand if need be.
if [ "$MODE" != "auth" ] && [ ! -f "$MAP_STORAGE_STATE" ] && { [ -z "$MAP_USER" ] || [ -z "$MAP_PASS" ]; }; then
  echo "ERROR: no saved session at $MAP_STORAGE_STATE and \$$USER_VAR/\$$PASS_VAR are empty." >&2
  echo "       Fix the env file, or run: bash run.sh --auth   (headed login, works with SSO/2FA)" >&2
  exit 1
fi

# ---------- run -------------------------------------------------------------
cd "$HERE"

if [ "$MODE" = "auth" ]; then
  export MAP_HEADED=1
  exec npx playwright test auth.setup.ts --config "$HERE/playwright.config.ts" --reporter=list
fi

[ -n "$TARGET" ] || { echo "ERROR: --target is required, e.g. --target /orders" >&2; exit 2; }
export MAP_TARGET="$TARGET"
[ -n "$TAG" ] && export MAP_TAG="$TAG"

echo "walking:  $MAP_BASE_URL$MAP_TARGET  ($ENV_NAME)"
echo "output:   $MAP_SCREENSHOT_DIR"
exec npx playwright test explore-page.spec.ts --config "$HERE/playwright.config.ts" --reporter=list
