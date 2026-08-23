#!/usr/bin/env python3
"""Build the screen canvas on React Flow.

Input:  screen-graph.full.json (screens, states, transitions)
        storyboard/comments.json (team comments, edited by hand and committed)
Output: storyboard/canvas.html + canvas.bundle.js + canvas.bundle.css
        — opens from disk, with no network and no external resources.

Only the layout is computed here: coordinates of cards, group frames and sticky notes.
Rendering, panning and zoom live in canvas-app (React + @xyflow/react); the same run builds
that bundle with esbuild. There is deliberately no auto-layout: the graph comes from the
frontend code, and the order of screens on the board must follow the user's path rather
than the convenience of an algorithm.
"""
import json
import math
import re
import subprocess
from datetime import date
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

CARD_W = 640            # screen card width; frames are captured at 1360 px and stay readable
STATE_W = 560           # card of a state inside a screen
META_H = 72             # caption strip under the frame
NO_SHOT_H = 200         # card with no frame
MAX_COL_H = 2400        # a column never grows taller — it wraps into the next one
IMG_MAX_H = {"route": 900, "state": 620}   # long forms are cropped from the top: what differs
                                           # between such frames sits in the upper part, and
                                           # showing them whole inflates the board fourfold
GAP_X, GAP_Y = 300, 48
STICKY_W = 258          # width of a comment sticky
STICKY_PAD = 24         # padding, top plus bottom
STICKY_LINE = 17        # text line height (12 px x 1.4)
STICKY_HEAD = 18        # the kind/author/date line
STICKY_CPL = 33         # characters per line at width 258 and size 12 (margin for wide glyphs)
SUB_GAP_X = 296         # between sub-columns of the same depth: room for a sticky
ZONE_PAD, ZONE_TOP = 56, 74
ZONE_GAP = 120
BOARD_MAX_W = 8800

# Board sections: order and titles come from the config; the two housekeeping ones are always
# added. A URL segment missing from the config lands in "service" instead of being dropped.
GROUPS = dict(CONFIG.get("groups") or {})
FAMILY_TITLES = {**GROUPS,
                 "service": CONFIG.get("service_group", "Service screens"),
                 "global": CONFIG.get("global_group", "From any screen")}
FAMILY_ORDER = ["global", *GROUPS, "service"]

def png_size(path: Path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                         capture_output=True, text=True).stdout
    w = re.search(r"pixelWidth:\s*(\d+)", out)
    h = re.search(r"pixelHeight:\s*(\d+)", out)
    return (int(w.group(1)), int(h.group(1))) if w and h else None


graph = json.loads((HERE / "screen-graph.full.json").read_text(encoding="utf-8"))
comments = json.loads((SB / "comments.json").read_text(encoding="utf-8"))["comments"]

nodes = {n["url"]: n for n in graph["nodes"] if n.get("kind") != "group"}
# the sidebar, the header and redirects lead away from any screen — in the graph that is source "*"
nodes["*"] = {
    "url": "*", "layer": "route", "kind": "global",
    "title": "From any screen",
    "frame_title": "Sidebar, header and redirects",
    "notes": [{"term": "What this is", "items": [],
               "text": "Not a screen but the navigation available everywhere: sidebar items, "
                       "links in the header, and the transitions the code performs on its own "
                       "(sign-out on an expired session, the redirect after login)."}],
    "flags": [], "tags": [], "roles": [],
    "source": "src/app/layout/components/sidebar/nav-data.ts",
}
edges = [e for e in graph["edges"] if e["from"] in nodes and e["to"] in nodes]


def family(url: str) -> str:
    if url == "*":
        return "global"
    base = url.split("#")[0]
    seg = base.strip("/").split("/")[0]
    return seg if seg in GROUPS else "service"


for url, n in nodes.items():
    n["family"] = family(n.get("of_route") or url)


def sticky_height(c: dict) -> int:
    """Sticky height from the text length: a fixed one cut comments off mid-word."""
    head = " · ".join(str(x) for x in (c.get("kind") or "note", c.get("author"), c.get("date")) if x)
    lines = sum(max(1, math.ceil(len(part) / STICKY_CPL)) for part in c.get("text", "").split("\n"))
    head_lines = max(1, math.ceil(len(head) / STICKY_CPL))
    return STICKY_PAD + head_lines * STICKY_HEAD + lines * STICKY_LINE


# ---------- how a card looks: the frame and its real proportions ----------
# Frames are captured at 1360 px wide; their height ranges from 900 to 3000+ for long forms.
# Card height is computed from the frame rather than fixed: otherwise a long form is squeezed
# into a strip and a short screen drowns in empty space.
THUMB_W = 680           # small frame for the overview
ZOOM_SHARP = 0.9        # from this zoom a visible card swaps in the full-size frame
THUMBS = SB / "assets-thumbs"


def thumb_for(shot: str):
    src = SB / shot
    if not src.exists():
        return None
    dst = THUMBS / shot.split("assets/", 1)[-1]
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["sips", "-Z", str(THUMB_W), str(src), "--out", str(dst)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None
    return "assets-thumbs/" + shot.split("assets/", 1)[-1]


state_child = {}
for e in edges:
    if e["kind"] == "state" and nodes[e["to"]].get("shot"):
        state_child.setdefault(e["from"], e["to"])

visual = {}
for u, n in nodes.items():
    shot, borrowed = n.get("shot"), None
    if not shot and u in state_child:                 # screen with no frame of its own — use a state frame
        child = nodes[state_child[u]]
        shot, borrowed = child["shot"], child.get("state")
    w = CARD_W if n["layer"] == "route" else STATE_W
    cropped = False
    if shot and (SB / shot).exists():
        size = png_size(SB / shot)
        full_h = round(w * size[1] / size[0]) if size else round(w * 0.66)
        img_h = min(full_h, IMG_MAX_H[n["layer"]])
        cropped = img_h < full_h
        h = img_h + META_H
    else:
        img_h, h = 0, NO_SHOT_H
    visual[u] = {"shot": thumb_for(shot) if shot else None, "shot_full": shot,
                 "borrowed": borrowed, "cropped": cropped, "w": w, "h": h, "img_h": img_h}

# ---------- layout inside a group ----------

groups = {}
for url, n in nodes.items():
    groups.setdefault(n["family"], []).append(url)

intra = {}
for e in edges:
    if nodes[e["from"]]["family"] == nodes[e["to"]]["family"]:
        intra.setdefault(e["from"], []).append(e["to"])

placed = {}
zones = []

for fam in FAMILY_ORDER:
    urls = sorted(groups.get(fam, []), key=lambda u: (u.count("/"), len(u), u))
    if not urls:
        continue
    incoming = {u: 0 for u in urls}
    for src, dsts in intra.items():
        if src in incoming:
            for d in dsts:
                if d in incoming:
                    incoming[d] += 1
    roots = [u for u in urls if incoming[u] == 0] or urls[:1]

    depth, order, queue = {}, [], list(roots)
    for r in roots:
        depth[r] = 0
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in intra.get(cur, []):
            if nxt not in depth:
                depth[nxt] = depth[cur] + 1
                queue.append(nxt)
    for u in urls:                       # nodes the traversal missed — column by address depth
        if u not in depth:
            depth[u] = u.count("/")
            order.append(u)

    columns = {}
    for u in order:
        columns.setdefault(depth[u], []).append(u)

    # columns are split by height: cards differ in height, and a dozen tall forms in one
    # column stretch the board several screens downwards
    zone_w = zone_h = 0
    x = ZONE_PAD
    layout = []
    for col in sorted(columns):
        chunks, cur, cur_h = [], [], 0
        for u in columns[col]:
            ch = visual[u]["h"]
            if cur and cur_h + ch > MAX_COL_H:
                chunks.append((cur, cur_h))
                cur, cur_h = [], 0
            cur.append(u)
            cur_h += ch + GAP_Y
        if cur:
            chunks.append((cur, cur_h))
        for ci, (chunk, h) in enumerate(chunks):
            layout.append({"col": col, "ci": ci, "chunk": chunk, "h": h - GAP_Y, "x": x})
        widest = max(visual[u]["w"] for u in columns[col])
        x += (len(chunks) - 1) * (STATE_W + SUB_GAP_X) + widest + GAP_X

    for l in layout:
        y = ZONE_TOP
        cx = l["x"] + l["ci"] * (STATE_W + SUB_GAP_X)
        for u in l["chunk"]:
            v = visual[u]
            placed[u] = {"x": cx, "y": y, "w": v["w"], "h": v["h"], "col": l["col"]}
            y += v["h"] + GAP_Y
            notes = comments.get(u, [])
            extra = STICKY_W + 18 if notes else 0
            notes_h = sum(sticky_height(c) + 14 for c in notes)
            zone_w = max(zone_w, cx + v["w"] + extra + ZONE_PAD)
            zone_h = max(zone_h, y + ZONE_PAD - GAP_Y, y - v["h"] - GAP_Y + notes_h + ZONE_PAD)

    zones.append({"family": fam, "title": FAMILY_TITLES[fam], "w": zone_w, "h": zone_h,
                  "count": len(urls)})

# ---------- placing groups on the board ----------

cursor_x = cursor_y = 0
row_h = 0
for z in zones:
    if cursor_x and cursor_x + z["w"] > BOARD_MAX_W:
        cursor_x, cursor_y, row_h = 0, cursor_y + row_h + ZONE_GAP, 0
    z["x"], z["y"] = cursor_x, cursor_y
    cursor_x += z["w"] + ZONE_GAP
    row_h = max(row_h, z["h"])

zone_by_family = {z["family"]: z for z in zones}
for u, pos in placed.items():
    z = zone_by_family[nodes[u]["family"]]
    pos["x"] += z["x"]
    pos["y"] += z["y"]

board_w = max(z["x"] + z["w"] for z in zones) + 200
board_h = max(z["y"] + z["h"] for z in zones) + 200

# ---------- payload for the page ----------

payload_nodes = []
for u, pos in placed.items():
    n, v = nodes[u], visual[u]
    payload_nodes.append({
        "id": u,
        "layer": n["layer"],
        "kind": n.get("kind"),
        "family": n["family"],
        "title": n.get("frame_title") or n.get("title") or u,
        "state": n.get("state"),
        "url": n.get("of_route") or u,
        "shot": v["shot"],
        "shot_full": v["shot_full"],
        "shot_borrowed": v["borrowed"],
        "img_h": v["img_h"],
        "cropped": v["cropped"],
        "storyboard": n.get("storyboard"),
        "roles": n.get("roles") or [],
        "tags": n.get("tags") or [],
        "flags": n.get("flags") or [],
        "notes": n.get("notes") or [],
        "source": n.get("source"),
        "x": pos["x"], "y": pos["y"], "w": pos["w"], "h": pos["h"],
        "comments": [dict(c, h=sticky_height(c)) for c in comments.get(u, [])],
    })

# The screen the board opens on. The overview will not do: at that zoom the frames are
# physically unreadable no matter how large the cards are.
start_at = CONFIG.get("start_at")
if start_at not in placed:
    first = next(iter(GROUPS), None)
    start_at = next((n["url"] for n in payload_nodes if n["family"] == first), payload_nodes[0]["id"])

payload = {
    "generated": str(date.today()),
    "zoom_sharp": ZOOM_SHARP,
    "start_at": start_at,
    "product": PRODUCT,
    "source": graph["source"],
    "board": {"w": board_w, "h": board_h},
    "zones": zones,
    "nodes": payload_nodes,
    "edges": [{"from": e["from"], "to": e["to"], "kind": e["kind"],
               "trigger": e["trigger"], "evidence": e.get("evidence", "")} for e in edges],
}

TEMPLATE = (HERE / "canvas-template.html").read_text(encoding="utf-8")
html = TEMPLATE.replace("/*__DATA__*/", json.dumps(payload, ensure_ascii=False))
(SB / "canvas.html").write_text(html, encoding="utf-8")

APP = HERE / "canvas-app"
if (APP / "node_modules").exists():
    r = subprocess.run(["npm", "run", "build", "--silent"], cwd=APP, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("bundle build failed:\n" + r.stdout + r.stderr)
else:
    print("! bundle not rebuilt: canvas-app/node_modules is missing — run npm install in canvas-app")

with_comments = sum(1 for n in payload_nodes if n["comments"])
print(f"canvas: {len(payload_nodes)} cards, {len(payload['edges'])} transitions, "
      f"{len(zones)} groups, comments on {with_comments} screens → {SB / 'canvas.html'}")
