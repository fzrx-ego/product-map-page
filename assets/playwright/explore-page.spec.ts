import { test, Page, Locator } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Read-only walkthrough of one screen.
 *
 *   bash run.sh --target /orders --tag orders [--dialogs] [--paginate]
 *
 * Navigates, switches tabs, optionally opens and closes dialogs, reads the DOM, screenshots.
 * It never submits, saves, deletes or uploads. Native confirm() dialogs are dismissed, never
 * accepted. Every locator below is a read.
 */

const BASE = required('MAP_BASE_URL');
const TARGET = required('MAP_TARGET');
const TAG =
  process.env.MAP_TAG || TARGET.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'screen';
const SHOTS = path.resolve(process.env.MAP_SCREENSHOT_DIR ?? path.join(__dirname, 'screenshots'));
const LOGIN_PATH = (process.env.MAP_LOGIN_PATH ?? '/auth/login').replace(/\/+$/, '');
const TRAVERSE_TABS = process.env.MAP_TRAVERSE_TABS !== '0';
const PROBE_DIALOGS = process.env.MAP_DIALOGS === '1';
const PAGINATE = process.env.MAP_PAGINATE === '1';
const SETTLE = Number(process.env.MAP_SETTLE_MS ?? 2500);

/** Labels that imply a write. Never clicked, in any mode. */
const WRITE_LABEL = /delete|remove|save|submit|send|pay|confirm|apply|upload|activate|deactivate|archive all|block|approve|reject/i;
/** Labels that open something to look at. Only these are clicked in --dialogs mode. */
const OPEN_LABEL = /^(add|new|create|filter|settings|columns|details|info|edit|view|configure|import)\b/i;

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is not set — run through run.sh, which loads the config`);
  return v;
}

const uniq = (a: string[]) =>
  [...new Set(a.map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean))];

const slug = (s: string) => s.replace(/[^a-z0-9]+/gi, '_').toLowerCase().slice(0, 40);

async function texts(page: Page, selector: string, maxLen = 120): Promise<string[]> {
  return page
    .locator(selector)
    .allInnerTexts()
    .then(a => uniq(a).filter(s => s.length <= maxLen))
    .catch(() => [] as string[]);
}

/** Problems the browser saw. A screen whose API returns 403 renders as an empty list; without
 *  this the map records "no data" and the defect stays invisible. */
type Problems = { consoleErrors: string[]; failedRequests: string[] };

function watchProblems(page: Page): Problems {
  const problems: Problems = { consoleErrors: [], failedRequests: [] };
  page.on('console', m => {
    if (m.type() === 'error') problems.consoleErrors.push(m.text().slice(0, 300));
  });
  page.on('pageerror', e => problems.consoleErrors.push(`pageerror: ${String(e).slice(0, 300)}`));
  page.on('requestfailed', r =>
    problems.failedRequests.push(`${r.method()} ${r.url()} — ${r.failure()?.errorText ?? 'failed'}`),
  );
  page.on('response', r => {
    if (r.status() >= 400) problems.failedRequests.push(`${r.status()} ${r.request().method()} ${r.url()}`);
  });
  // A native confirm() must never be accepted: accepting it is a write.
  page.on('dialog', d => void d.dismiss().catch(() => {}));
  return problems;
}

async function rowCount(page: Page): Promise<number> {
  const tableRows = await page.locator('table tbody tr').count().catch(() => 0);
  if (tableRows > 0) return tableRows;
  const ariaRows = await page.locator('[role=row]').count().catch(() => 0);
  const headerRows = await page.locator('[role=row]:has([role=columnheader])').count().catch(() => 0);
  return Math.max(0, ariaRows - headerRows);
}

async function snapshot(page: Page, tag: string, problems: Problems, requested?: string) {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(SETTLE);

  const current = new URL(page.url());
  if (LOGIN_PATH && current.pathname.includes(LOGIN_PATH)) {
    throw new Error(
      'Landed on the login page: the saved session expired. Re-run `run.sh --auth`. ' +
        'Do NOT record this as "access restricted for this role".',
    );
  }

  const data = {
    tag,
    requestedUrl: requested ?? null,
    url: page.url(),
    // A silent redirect turns "/orders shows a dashboard" into a fact in the map. Flag it.
    redirected: requested ? !page.url().startsWith(requested) : false,
    title: await page.title().catch(() => ''),
    headings: await texts(page, 'h1, h2, h3, [class*="title" i]', 150),
    tabs: await texts(page, '[role=tab], [class*="tab" i] button, [class*="tab" i] a', 60),
    columns: await texts(page, 'table thead th, [role=columnheader], [class*="thead" i] th', 60),
    buttons: await texts(page, 'button:visible, [role=button]:visible', 60),
    links: uniq(
      await page
        .locator('a[href]:visible')
        .evaluateAll(els =>
          els.map(e => `${(e.textContent ?? '').trim()} → ${e.getAttribute('href')}`),
        )
        .catch(() => [] as string[]),
    ),
    // names only: reading which inputs exist, never typing into them
    fields: uniq(
      await page
        .locator('input:visible, select:visible, textarea:visible')
        .evaluateAll(els =>
          els.map(e => {
            const el = e as HTMLInputElement;
            return [el.tagName.toLowerCase(), el.type || '', el.name || el.id || '',
                    el.placeholder || ''].filter(Boolean).join(' | ');
          }),
        )
        .catch(() => [] as string[]),
    ),
    emptyState: await texts(page, '[class*="empty" i], [class*="no-data" i], [class*="placeholder" i]', 200),
    rowCount: await rowCount(page),
    consoleErrors: uniq(problems.consoleErrors).slice(0, 20),
    failedRequests: uniq(problems.failedRequests).slice(0, 20),
  };

  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${tag}.png`), fullPage: true }).catch(() => {});
  fs.writeFileSync(path.join(SHOTS, `${tag}.json`), JSON.stringify(data, null, 2), 'utf8');

  console.log(`\n══════ ${tag} ══════  ${data.url}`);
  if (data.redirected) console.log(`REDIRECTED from ${data.requestedUrl}`);
  for (const [k, v] of Object.entries(data)) {
    if (['tag', 'url', 'requestedUrl', 'redirected'].includes(k)) continue;
    console.log(`${k}:`, Array.isArray(v) ? v.slice(0, 25) : v);
  }
  return data;
}

/** Tabs are not always [role=tab]. Collect candidates, report honestly when none are clickable. */
async function tabHandles(page: Page): Promise<Locator[]> {
  for (const sel of ['[role=tab]', '[class*="tab" i] button', '[class*="tab" i] a', 'nav a[class*="tab" i]']) {
    const loc = page.locator(`${sel}:visible`);
    if ((await loc.count().catch(() => 0)) > 1) {
      const n = await loc.count();
      return Array.from({ length: n }, (_, i) => loc.nth(i));
    }
  }
  return [];
}

async function closeOverlay(page: Page) {
  const cancel = page
    .locator('[role=dialog] button, .modal button, [class*="dialog" i] button')
    .filter({ hasText: /cancel|close|отмена|закрыть|abbrechen|annuler/i })
    .first();
  if (await cancel.count().catch(() => 0)) {
    await cancel.click({ timeout: 5000 }).catch(() => {});
  } else {
    await page.keyboard.press('Escape').catch(() => {});
  }
  await page.waitForTimeout(600);
}

test('walk one screen, read only', async ({ page }) => {
  const problems = watchProblems(page);
  const requested = `${BASE}${TARGET}`;

  await page.goto(requested, { waitUntil: 'domcontentloaded' });
  const main = await snapshot(page, `${TAG}_main`, problems, requested);

  // ---- tabs ----------------------------------------------------------------
  if (TRAVERSE_TABS && main.tabs.length > 0) {
    const handles = await tabHandles(page);
    if (handles.length === 0 && main.tabs.length > 1) {
      console.log(
        `\nWARNING: ${main.tabs.length} tab labels were read but none are clickable with the ` +
          `built-in selectors. Tabs were NOT traversed — extend tabHandles() for this product ` +
          `before recording tab contents.`,
      );
    }
    for (const [i, handle] of handles.entries()) {
      const label = (await handle.innerText().catch(() => `tab_${i}`)).trim();
      if (WRITE_LABEL.test(label)) {
        console.log(`  skipped tab "${label}" — label implies a write`);
        continue;
      }
      await handle.click({ timeout: 15_000 }).catch(() => {});
      await snapshot(page, `${TAG}_tab_${i}_${slug(label)}`, problems);
    }
  }

  // ---- dialogs (opt-in) ----------------------------------------------------
  if (PROBE_DIALOGS) {
    await page.goto(requested, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(SETTLE);
    const openers = main.buttons.filter(b => OPEN_LABEL.test(b) && !WRITE_LABEL.test(b));
    for (const [i, label] of openers.entries()) {
      const btn = page.locator('button:visible', { hasText: label }).first();
      if (!(await btn.count().catch(() => 0))) continue;
      await btn.click({ timeout: 10_000 }).catch(() => {});
      await page.waitForTimeout(800);
      const dialog = page.locator('[role=dialog], .modal, [class*="dialog" i]').first();
      if (await dialog.count().catch(() => 0)) {
        await snapshot(page, `${TAG}_dialog_${i}_${slug(label)}`, problems);
      } else {
        console.log(`  "${label}" opened no dialog — skipped`);
      }
      await closeOverlay(page);
    }
  }

  // ---- pagination (opt-in) -------------------------------------------------
  if (PAGINATE) {
    const next = page
      .locator('button:visible, a:visible, [role=button]:visible')
      .filter({ hasText: /^(next|›|»|вперёд|следующая)$/i })
      .or(page.locator('[aria-label*="next" i]:visible, .p-paginator-next:visible'))
      .first();
    if (await next.count().catch(() => 0)) {
      await next.click({ timeout: 10_000 }).catch(() => {});
      await snapshot(page, `${TAG}_page2`, problems);
    } else {
      console.log('  no pagination control found');
    }
  }
});
