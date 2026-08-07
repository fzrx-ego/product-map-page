import { defineConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HERE = __dirname;
const STORAGE_STATE = process.env.MAP_STORAGE_STATE ?? path.join(HERE, '.auth', 'state.json');
// Accepts "1600x1000" and the config's list form "[1600, 1000]".
const [w, h] = (process.env.MAP_VIEWPORT || '1600x1000')
  .replace(/[[\]]/g, '')
  .split(/[x,]/)
  .map(s => Number(s.trim()));

export default defineConfig({
  testDir: HERE,
  // auth.setup.ts does not match Playwright's default *.spec.ts pattern
  testMatch: ['**/*.spec.ts', '**/auth.setup.ts'],
  // A walkthrough is navigation plus deliberate settle waits, not a unit test.
  // The default 30 s expires mid-run and looks like a broken screen.
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  outputDir: path.join(HERE, '.test-results'),
  use: {
    baseURL: process.env.MAP_BASE_URL,
    headless: process.env.MAP_HEADED === '1' ? false : true,
    viewport: { width: w || 1600, height: h || 1000 },
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
    ignoreHTTPSErrors: true,
    // Reuse a saved session when one exists; auth.setup.ts creates it.
    storageState: fs.existsSync(STORAGE_STATE) ? STORAGE_STATE : undefined,
  },
});
