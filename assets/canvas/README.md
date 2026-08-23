# Canvas toolchain

Copy this folder into the repository being documented (a `scripts/` folder is the usual place),
edit `canvas.config.json`, and run the three scripts. Nothing here reaches outside the folder
except through that config.

```
canvas.config.json          copied from canvas.config.example.json and edited
extract_routes_angular.py   routes and transitions from an Angular frontend
link_storyboard.py          attaches storyboard frames, adds in-screen states
build_canvas.py             computes the layout, generates previews, builds the board
canvas-template.html        page shell
canvas-app/                 React Flow app; npm install here once
  package.json              dependencies pinned to exact versions
  package-lock.json         shipped on purpose: the bundle must build the same way later
  build.mjs                 esbuild → canvas.bundle.js + canvas.bundle.css
  src/app.jsx               nodes, edges, panels
  src/tokens.css            design tokens — the only place colours and sizes are defined
  src/styles.css            everything the tokens are used for
```

Three files hold project data and stay in the repository next to these scripts:
`edges-manual.json`, `states-manual.json` and — beside the storyboard — `comments.json`.

Requirements: Python 3 (no packages), Node 18+, and `sips` for frame previews (macOS; on Linux
replace the one `subprocess.run(["sips", …])` call in `build_canvas.py` with ImageMagick).

The full rationale, the graph schema and the traps already stepped in: `references/canvas.md`.
