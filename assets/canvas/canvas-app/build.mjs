// Canvas build: one IIFE bundle plus its css, next to canvas.html.
// IIFE rather than an ES module: the page opens from disk, and file:// forbids module scripts.
// The output path comes from canvas.config.json next to the scripts, so there is one path for all.
import { build } from 'esbuild';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const config = JSON.parse(readFileSync(resolve(here, '..', 'canvas.config.json'), 'utf8'));

function findRoot(from) {
  let dir = from;
  for (;;) {
    if (existsSync(resolve(dir, config.storyboard))) return dir;
    const up = dirname(dir);
    if (up === dir) throw new Error(`project root not found: no ${config.storyboard} directory above ${from}`);
    dir = up;
  }
}

const out = resolve(findRoot(here), config.storyboard, 'canvas.bundle.js');

await build({
  entryPoints: [resolve(here, 'src/app.jsx')],
  bundle: true,
  format: 'iife',
  target: ['safari16', 'chrome110'],
  minify: true,
  sourcemap: false,
  outfile: out,
  loader: { '.js': 'jsx', '.woff2': 'dataurl', '.woff': 'dataurl', '.ttf': 'dataurl' },
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'info',
});
