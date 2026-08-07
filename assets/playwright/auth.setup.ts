import { test, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Run once per environment:  bash run.sh --auth
 *
 * Opens a visible browser, logs in — scripted if credentials are present, by hand otherwise —
 * and saves the session. Every later run reuses it, so SSO, 2FA and captcha are handled by a
 * human once instead of being fought with selectors forever.
 */

const BASE = required('MAP_BASE_URL');
const LOGIN_PATH = (process.env.MAP_LOGIN_PATH ?? '/auth/login').replace(/\/+$/, '');
/** For products that log in without changing the URL — a modal, or a login at `/`. */
const SUCCESS_SELECTOR = process.env.MAP_SUCCESS_SELECTOR ?? '';
const USER = process.env.MAP_USER ?? '';
const PASS = process.env.MAP_PASS ?? '';
const MANUAL = process.env.MAP_MANUAL_AUTH === '1' || !USER || !PASS;
const STORAGE_STATE = process.env.MAP_STORAGE_STATE ?? path.join(__dirname, '.auth', 'state.json');

const USER_SEL = process.env.MAP_USER_SELECTOR
  ?? 'input[type=email], input[name=email], input[name=username], input[formcontrolname=username], input[autocomplete=username]';
const PASS_SEL = process.env.MAP_PASS_SELECTOR
  ?? 'input[type=password], input[name=password], input[formcontrolname=password]';
const SUBMIT_SEL = process.env.MAP_SUBMIT_SELECTOR ?? 'button[type=submit], input[type=submit]';

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set — run through run.sh, which loads the config`);
  return v;
}

async function scriptedLogin(page: Page) {
  await page.locator(USER_SEL).first().fill(USER);
  await page.locator(PASS_SEL).first().fill(PASS);
  // .first() matters: a page with two submit buttons otherwise fails on strict mode
  await page.locator(SUBMIT_SEL).first().click();
}

test('save authenticated session', async ({ page }) => {
  test.setTimeout(600_000); // a human may be typing a one-time code

  await page.goto(`${BASE}${LOGIN_PATH}`, { waitUntil: 'domcontentloaded' });

  if (MANUAL) {
    console.log('\n  Log in in the browser window. Waiting until the login page is left…\n');
  } else {
    await scriptedLogin(page);
  }

  const timeout = MANUAL ? 570_000 : 60_000;
  if (SUCCESS_SELECTOR) {
    await page.locator(SUCCESS_SELECTOR).first().waitFor({ state: 'visible', timeout });
  } else if (LOGIN_PATH && LOGIN_PATH !== '/') {
    await page.waitForURL(url => !url.pathname.includes(LOGIN_PATH), { timeout });
  } else {
    // Nothing to wait for: no login path to leave and no success marker configured.
    throw new Error(
      'MAP_SUCCESS_SELECTOR is required when the login page has no distinct path — ' +
        'set auth.success_selector in map.config.yml to something visible only after login.',
    );
  }
  await page.waitForLoadState('networkidle').catch(() => {});

  fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true });
  await page.context().storageState({ path: STORAGE_STATE });
  console.log(`  Session saved: ${STORAGE_STATE}`);
  console.log(`  Landed on: ${page.url()}`);
});
