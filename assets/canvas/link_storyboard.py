#!/usr/bin/env python3
"""Attach storyboard frames to the route graph and add the states inside each screen.

Input: screen-graph.json (routes from code) + the HTML storyboards.
Output: screen-graph.full.json — nodes on two layers (route and in-screen state), transition
edges, and for every node a link to its frame and to its written explanation.

The frame caption (`visual-cap`) is the join key: "Desktop · /items/:id/settings · Advanced".
Whatever follows the address is a state inside the screen: a tab, a mode, an empty list,
a wizard step. Nesting of modes (a mode inside another mode) is declared in states-manual.json:
it cannot be derived from the caption, and guessing it would be lying.
"""
import json
import re
from html import unescape
from pathlib import Path

# ---------- paths ----------
# The project root is found by walking up from this script: the first directory that
# contains the storyboard folder. Moving the toolchain to another project is one config edit.
HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "canvas.config.json").read_text(encoding="utf-8"))


def find_root() -> Path:
    for base in [HERE, *HERE.parents]:
        if (base / CONFIG["storyboard"]).is_dir():
            return base
    raise SystemExit(f"project root not found: no {CONFIG['storyboard']} directory above {HERE}")


ROOT = find_root()
SB = ROOT / CONFIG["storyboard"]
FRONTEND = ROOT / CONFIG["frontend"]
PRODUCT = CONFIG.get("product", "")
SKIP = {"index.html"}   # add here any storyboard file that is a duplicate or a mock, not a screen

graph = json.loads((HERE / "screen-graph.json").read_text(encoding="utf-8"))
routes = {n["url"]: n for n in graph["nodes"]}
nodes = [dict(n, layer="route") for n in graph["nodes"]]
edges = [dict(e, layer="route") for e in graph["edges"]]

manual_file = HERE / "states-manual.json"
manual = json.loads(manual_file.read_text(encoding="utf-8")) if manual_file.exists() else {}
parent_of = manual.get("parent_of", {})
route_of_anchor = manual.get("route_of_anchor", {})


def manual_route(file_name: str, anchor: str):
    """Frames whose caption carries no address: attached by anchor prefix."""
    for key, url in route_of_anchor.items():
        f, _, prefix = key.partition("#")
        if f == file_name and anchor.startswith(prefix):
            return url
    return None

warn = []


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def notes_of(body: str):
    """The explanation next to the frame: term/definition pairs plus the flagged notes."""
    dl = re.search(r"<dl>(.*?)</dl>", body, re.S)
    pairs = []
    if dl:
        for m in re.finditer(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", dl.group(1), re.S):
            items = re.findall(r"<li>(.*?)</li>", m.group(2), re.S)
            pairs.append({
                "term": text_of(m.group(1)),
                "text": text_of(re.sub(r"<ul>.*?</ul>", "", m.group(2), flags=re.S)),
                "items": [text_of(i) for i in items],
            })
    flags = [text_of(f) for f in re.findall(r'<div class="flag">(.*?)</div>', body, re.S)]
    tags = [text_of(t) for t in re.findall(r'<span class="tag[^"]*">(.*?)</span>', body, re.S)]
    return pairs, flags, tags


frames = []
for f in sorted(SB.glob("*.html")):
    if f.name in SKIP:
        continue
    html = f.read_text(encoding="utf-8")
    last_route = None
    for m in re.finditer(r'<article class="row"[^>]*id="([^"]+)"(.*?)</article>', html, re.S):
        anchor, body = m.group(1), m.group(2)
        cap_m = re.search(r'class="visual-cap">(.*?)</p>', body, re.S)
        h3 = re.search(r"<h3>(.*?)</h3>", body, re.S)
        img = re.search(r'<img src="([^"]+)"', body)
        cap = text_of(cap_m.group(1)) if cap_m else ""
        notes, flags, tags = notes_of(body)
        parts = [p.strip() for p in re.split(r"\s·\s", cap) if p.strip()]
        route = next((p for p in parts if p.startswith("/")), None) or manual_route(f.name, anchor)
        if route:
            last_route = route
        elif cap and last_route:      # caption present but no address — a state of the same screen
            route = last_route
        state = " · ".join(p for p in parts if not p.startswith("/") and p not in ("Desktop", "Mobile"))
        frames.append({
            "file": f.name,
            "anchor": anchor,
            "route": route,
            "state": state,
            "title": text_of(h3.group(1)) if h3 else anchor,
            "shot": img.group(1) if img else None,
            "storyboard": f"{f.name}#{anchor}",
            "notes": notes,
            "flags": flags,
            "tags": tags,
        })

# state nodes and the transitions into them
for fr in frames:
    if not fr["route"]:
        warn.append(f"frame `{fr['storyboard']}` is not attached to a route — its caption has no address")
        continue
    if fr["route"] not in routes:
        warn.append(f"frame `{fr['storyboard']}` points at `{fr['route']}`, which is not in the route tree")
    if not fr["state"]:
        for n in nodes:                       # a frame of the screen itself hangs on the route node
            if n["url"] == fr["route"] and n.get("layer") == "route":
                if n.get("shot") and not fr["shot"]:
                    continue          # a frame is already attached — never overwrite it with an empty one
                n.update(storyboard=fr["storyboard"], shot=fr["shot"], frame_title=fr["title"],
                         notes=fr["notes"], flags=fr["flags"], tags=fr["tags"])
        continue
    node_id = f"{fr['route']}#{fr['anchor']}"
    nodes.append({
        "url": node_id, "layer": "state", "of_route": fr["route"], "kind": "state",
        "title": fr["title"], "state": fr["state"],
        "storyboard": fr["storyboard"], "shot": fr["shot"],
        "notes": fr["notes"], "flags": fr["flags"], "tags": fr["tags"],
    })
    parent = parent_of.get(fr["storyboard"], fr["route"])
    edges.append({
        "from": parent, "to": node_id, "trigger": fr["state"],
        "kind": "state", "layer": "state", "evidence": fr["storyboard"],
    })

# routes with no frame at all
shot_routes = {f["route"] for f in frames}
tab_hosts = {e["from"] for e in edges if e.get("kind") == "tab"}
for url, n in routes.items():
    if n["kind"] in ("group", "redirect") or url in tab_hosts or url in ("/logout", "/"):
        continue
    if url not in shot_routes:
        warn.append(f"route `{url}` exists in code but has no frame in the storyboard")

out = {
    "generated": graph["generated"],
    "source": graph["source"],
    "nodes": nodes,
    "edges": edges,
}
(HERE / "screen-graph.full.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
(HERE / "storyboard-gaps.md").write_text(
    "# Where the storyboard and the code disagree\n\n" + "\n".join(f"- {w}" for w in warn) + "\n", encoding="utf-8")

print(f"nodes: {len(nodes)} (routes {len(routes)}, states {len(nodes)-len(routes)})  "
      f"edges: {len(edges)}  disagreements: {len(warn)}")
