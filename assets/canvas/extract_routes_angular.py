#!/usr/bin/env python3
"""Extract the screen graph from an Angular frontend: route nodes and transition edges.

Input: the local frontend checkout named in the config.
Output, next to this script: screen-graph.json + unresolved.md.

Parsing is textual — no tree-sitter, no packages to install. Angular declares its routes as
uniform object literals, so bracket matching is enough. Anything this script fails to read
lands in unresolved.md instead of being dropped silently. Edges that cannot be derived from
code at all (transitions through dialogs, links built at runtime) are written by hand into
edges-manual.json, which is merged into the extracted set.

This is the reference implementation for Angular. Another stack needs its own extractor;
what matters is that it emits the same screen-graph.json shape (see references/canvas.md).
"""
import json
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
SRC = FRONTEND / "src" / "app"
OUT = HERE

unresolved = []
nodes = {}
edges = []


def rel(p: Path) -> str:
    return str(p.relative_to(FRONTEND))


def note(msg: str):
    unresolved.append(msg)


# ---------- literal parsing ----------

def balanced(text: str, start: int, open_ch: str, close_ch: str):
    depth, i = 0, start
    while i < len(text):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return text[start + 1 : i]
        i += 1
    return None


def routes_literal(text: str):
    m = re.search(r"const\s+routes\s*:\s*Routes\s*=\s*\[", text)
    if not m:
        return None
    return balanced(text, text.index("[", m.start()), "[", "]")


def split_objects(body: str):
    objs, depth, start = [], 0, None
    for i, ch in enumerate(body):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objs.append(body[start + 1 : i])
                start = None
    return objs


def field(obj: str, name: str):
    m = re.search(rf"(?<![\w.]){name}\s*:\s*", obj)
    if not m:
        return None
    rest = obj[m.end() :].lstrip()
    if rest[:1] in "'\"`":
        q = rest[0]
        return rest[1 : rest.index(q, 1)]
    return rest.split(",")[0].split("\n")[0].strip()


def data_body(obj: str) -> str:
    """The whole `data: { ... }` body — field() stops at the first comma and loses backUrl."""
    m = re.search(r"(?<![\w.])data\s*:\s*\{", obj)
    if not m:
        return ""
    return balanced(obj, obj.index("{", m.start()), "{", "}") or ""


def children_body(obj: str):
    m = re.search(r"children\s*:\s*\[", obj)
    return balanced(obj, obj.index("[", m.start()), "[", "]") if m else None


def tab_name(obj: str):
    data = data_body(obj)
    m = re.search(r"tab\s*:\s*['\"]([^'\"]+)['\"]", data) or re.search(r"tab\s*:\s*TERMINAL_TABS\.(\w+)", data)
    return m.group(1) if m else None


def child_routes_file(obj: str, module_file: Path):
    """The child module's route file. loadChildren only: loadComponent pulls in a single
    component rather than a set of routes, so there is nothing to walk into."""
    lc = re.search(r"loadChildren\s*:", obj)
    if not lc:
        return None
    m = re.search(r"import\(\s*['\"]([^'\"]+)['\"]", obj[lc.end():])
    if not m:
        return None
    mod = (module_file.parent / m.group(1)).resolve()
    routing = mod.with_name(mod.name.replace(".module", "-routing.module") + ".ts")
    if routing.exists():
        return routing
    module_ts = Path(str(mod) + ".ts")          # routes declared inline in the module (auth does this)
    return module_ts if module_ts.exists() else None


def own_fields(obj: str) -> str:
    """The object body without its nested children: otherwise component and title leak up from a child."""
    m = re.search(r"children\s*:\s*\[", obj)
    if not m:
        return obj
    inner = balanced(obj, obj.index("[", m.start()), "[", "]")
    return obj.replace(inner, "") if inner else obj


def component_of(obj: str):
    """The route's component class. loadComponent is handled separately; `component:` is read
    only as a route field — otherwise the regex catches the parameter inside canDeactivate."""
    m = re.search(r"loadComponent\s*:", obj)
    if m:
        tail = obj[m.end():]
        cls = re.search(r"m\.(\w+)", tail) or re.search(r"then\(\s*\w*\s*=>\s*\w+\.(\w+)", tail)
        if cls:
            return cls.group(1)
        path = re.search(r"import\(\s*['\"]([^'\"]+)['\"]", tail)
        if path:
            stem = Path(path.group(1)).name.replace(".component", "")
            return "".join(w.capitalize() for w in stem.split("-")) + "Component"
    m = re.search(r"(?:^|[,{\s])component\s*:\s*(\w+)\s*[,}\n]", obj)
    return m.group(1) if m else None


def add_node(url, obj, source, kind_hint=None):
    obj = own_fields(obj)
    comp = component_of(obj)
    tab = tab_name(obj)
    redirect = field(obj, "redirectTo")
    kind = kind_hint or ("redirect" if redirect else "tab" if tab else "screen" if comp else "group")
    node = {
        "url": url,
        "title": field(obj, "title"),
        "tab": tab,
        "component": comp,
        "kind": kind,
        "roles": re.findall(r"CompanyRoles\.(\w+)", obj),
        "guards": re.findall(r"(\w*[Gg]uard)", field(obj, "canActivate") or ""),
        "redirect_to": redirect,
        "back_url": (lambda m: m.group(1) if m else None)(re.search(r"backUrl\s*:\s*'([^']*)'", data_body(obj))),
        "source": source,
    }
    if url not in nodes or nodes[url]["kind"] == "group":
        nodes[url] = node


def walk_objects(body: str, prefix: str, routes_file: Path, seen):
    for obj in split_objects(body):
        path = field(obj, "path")
        if path is None or path == "**":
            continue
        url = "/".join(x for x in [prefix.rstrip("/"), path] if x)
        url = "/" + url.lstrip("/") if url else (prefix or "/")
        add_node(url, obj, rel(routes_file))

        kids = children_body(obj)
        if kids:
            walk_objects(kids, url, routes_file, seen)

        target = child_routes_file(obj, routes_file)
        if target:
            walk_file(target, url, seen)
        elif "loadChildren" in obj:
            note(f"unresolved loadChildren: `{rel(routes_file)}` → `{url}`")


def walk_file(routes_file: Path, prefix: str, seen: frozenset):
    if routes_file in seen:
        return
    seen = seen | {routes_file}
    body = routes_literal(routes_file.read_text(encoding="utf-8"))
    if body is None:
        note(f"no `const routes: Routes` literal in `{rel(routes_file)}`")
        return
    walk_objects(body, prefix, routes_file, seen)


walk_file(SRC / "app-routing.module.ts", "", frozenset())

# ---------- where a component lives ----------

by_component = {}
for url, n in nodes.items():
    if n.get("component"):
        by_component.setdefault(n["component"], []).append(url)


def host_urls(path: Path):
    """Routes a component sits on. Shared tabs live on two branches at once, so this is a list."""
    stem = path.name.replace(".component.html", "").replace(".component.ts", "")
    cls = "".join(w.capitalize() for w in stem.split("-")) + "Component"
    return by_component.get(cls, [])


# ---------- edges ----------

def param_child(host: str):
    """The child route carrying a parameter: /items -> /items/:id."""
    if not host:
        return None
    for url in nodes:
        if url.startswith(host.rstrip("/") + "/:") and "/" not in url[len(host) + 1:]:
            return url
    return None


def add_edge(src, dst, trigger, kind, evidence):
    edges.append({"from": src or "*", "to": dst, "trigger": trigger, "kind": kind, "evidence": evidence})


# sidebar menu
nav_file = SRC / "layout" / "components" / "sidebar" / "nav-data.ts"
nav = nav_file.read_text(encoding="utf-8")
nav_start = re.search(r"navbarData\s*:[^=]*=\s*\[", nav) or re.search(r"=\s*\[", nav)
nav_body = balanced(nav, nav_start.end() - 1, "[", "]")   # end()-1 is the array's opening bracket
for obj in split_objects(nav_body):
    if all(ln.strip().startswith("//") for ln in obj.strip().splitlines() if ln.strip()):
        continue
    link, label = field(obj, "routeLink"), field(obj, "label")
    if not link:
        continue
    add_edge("*", "/" + link.lstrip("/"), f"sidebar menu — \u201c{label}\u201d", "sidebar", rel(nav_file))

# labels of tabs and buttons: string enums and i18n keys
LABELS = {}
for ts in SRC.rglob("*.ts"):
    txt = ts.read_text(encoding="utf-8")
    for en in re.finditer(r"export enum (\w+)\s*\{([^}]*)\}", txt):
        for k, v in re.findall(r"(\w+)\s*=\s*'([^']*)'", en.group(2)):
            LABELS[f"{en.group(1)}.{k}"] = v

I18N = {}
i18n_file = FRONTEND / "src" / "assets" / "i18n" / "en.json"
if i18n_file.exists():
    def flatten(d, prefix=""):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            flatten(v, key) if isinstance(v, dict) else I18N.setdefault(key, v)
    flatten(json.loads(i18n_file.read_text(encoding="utf-8")))


def label_text(raw: str) -> str:
    """The label as the user sees it: enum member → its value, i18n key → its translation."""
    if not raw:
        return raw
    return LABELS.get(raw) or I18N.get(raw) or raw


# tabs inside record cards: tabItems arrays in components (label + routerLink [+ roles])
for ts in sorted(SRC.rglob("*.component.ts")):
    text = ts.read_text(encoding="utf-8")
    if "routerLink:" not in text:
        continue
    hosts = host_urls(ts)
    if not hosts:
        continue
    for obj in re.finditer(r"\{[^{}]*routerLink\s*:\s*'([^']+)'[^{}]*\}", text):
        link = obj.group(1)
        label = label_text(field(obj.group(0), "label") or link)
        roles = re.findall(r"CompanyRoles\.(\w+)", obj.group(0))
        line = text[: obj.start()].count("\n") + 1
        ev = f"{rel(ts)}:{line}"
        for host in hosts:
            # routerLink: 'id' in a row menu means the record's id, not a literal path segment
            seg = ":id" if link == "id" else link
            dst = seg if seg.startswith("/") else host.rstrip("/") + "/" + seg
            kind = "row-action" if seg == ":id" else "tab"
            trig = (f"row menu \u201c\u22ee\u201d — \u201c{label}\u201d" if kind == "row-action" else f"tab \u201c{label}\u201d")
            trig += f" ({', '.join(roles)} only)" if roles else ""
            add_edge(host, dst, trig, kind, ev)

# routerLink in templates
for tpl in sorted(SRC.rglob("*.component.html")):
    text = tpl.read_text(encoding="utf-8")
    hosts = host_urls(tpl) or [None]
    for m in re.finditer(r"\[?routerLink\]?\s*=\s*\"([^\"]+)\"", text):
        raw = m.group(1).strip()
        line = text[: m.start()].count("\n") + 1
        head = text.rfind("<", 0, m.start())
        tag = re.match(r"<(\w+)", text[head : head + 14])
        tagname = tag.group(1).lower() if tag else "?"
        ev = f"{rel(tpl)}:{line}"
        lit = re.fullmatch(r"'([^']*)'|\[\s*'([^']*)'\s*\]", raw)
        if lit:
            target = lit.group(1) or lit.group(2) or ""
        elif re.fullmatch(r"[/\w\-]+", raw):   # routerLink="/items" with no quotes inside
            target = raw
        else:
            target = None
        for host in hosts:
            if target and target.startswith("/"):
                add_edge(host, target, f"<{tagname}>", "routerLink", ev)
            elif target == "new" and host:
                add_edge(host, host + "/new", f"<{tagname}> — create button", "routerLink", ev)
            elif target and target.startswith("../") and host:
                base = host.rsplit("/", target.count("../"))[0]
                add_edge(host, base + "/" + target.replace("../", ""), f"<{tagname}> — back", "routerLink", ev)
            elif raw in ("[navItem.routeLink]", "item.routerLink") or (
                tagname == "a" and "['id']" in raw and any(
                    e["kind"] == "row-action" and e["from"] == host for e in edges)):
                pass          # already collected by the nav-data and actionItems/tabItems passes
            elif host and tagname == "tr" and "['id']" in raw:
                child = param_child(host)
                if child:
                    add_edge(host, child, "click on a list row", "row-click", ev)
                else:
                    note(f"list row on `{host}` opens a record but no child route was found ({ev})")
            elif host and raw == "backUrl":
                back = nodes.get(host, {}).get("back_url")
                if back:
                    add_edge(host, back, "Back button", "back", ev)
                else:
                    note(f"`backUrl` on `{host}` is not set in the route data ({ev})")
            else:
                note(f"link `{raw}` in `{ev}` (screen {host or 'unknown'}) — target must be written by hand")

# navigate / navigateByUrl
for ts in sorted(SRC.rglob("*.ts")):
    text = ts.read_text(encoding="utf-8")
    hosts = host_urls(ts) or [None]
    for m in re.finditer(r"navigateByUrl\(\s*['\"]([^'\"]+)['\"]|navigate\(\s*\[\s*['\"]([^'\"]+)['\"]", text):
        dst = (m.group(1) or m.group(2)).strip()
        line = text[: m.start()].count("\n") + 1
        ev = f"{rel(ts)}:{line}"
        if dst.startswith(".."):
            note(f"relative navigate `{dst}` in `{ev}` — target must be written by hand")
            continue
        for host in hosts:
            add_edge(host, "/" + dst.lstrip("/"), "navigation from component code", "navigate", ev)

# opening a record from a row menu: navigate([selectedItem?.id], {relativeTo: route})
for ts in sorted(SRC.rglob("*.component.ts")):
    text = ts.read_text(encoding="utf-8")
    for m in re.finditer(r"navigate\(\s*\[\s*this\.(\w+)\??\.id\s*\][^)]*relativeTo", text):
        line = text[: m.start()].count("\n") + 1
        ev = f"{rel(ts)}:{line}"
        for host in host_urls(ts) or []:
            child = param_child(host)
            if child:
                add_edge(host, child, "row menu \u201c\u22ee\u201d — open record", "row-action", ev)
            else:
                note(f"navigate by id on `{host}` — no child route with a parameter ({ev})")

# hand-written edges
manual_file = OUT / "edges-manual.json"
manual = json.loads(manual_file.read_text(encoding="utf-8")) if manual_file.exists() else []
for e in manual:
    e["kind"] = "manual"
edges.extend(manual)

# create screens: no route of their own, the router serves them through :id with the value new
for e in list(edges):
    if e["to"].endswith("/new") and e["to"] not in nodes:
        parent = e["to"].rsplit("/", 1)[0]
        via = param_child(parent)
        nodes[e["to"]] = {
            "url": e["to"], "title": None, "tab": None,
            "component": nodes.get(via, {}).get("component"),
            "kind": "create", "roles": [], "guards": [], "redirect_to": None, "back_url": None,
            "source": f"served by route {via} with the value new" if via else "route not found",
        }

# check every target against the route tree
known = set(nodes)
for e in edges:
    if e["to"] not in known and not any(e["to"].startswith(u.split("/:")[0] + "/") for u in known):
        note(f"transition points at an unknown route `{e['to']}` ({e['evidence']})")

merged = {}
for e in edges:
    key = (e["from"], e["to"], e["trigger"])
    if key in merged:
        prev = merged[key]["evidence"]
        if e["evidence"] not in prev.split("; "):
            merged[key]["evidence"] = prev + "; " + e["evidence"]
    else:
        merged[key] = dict(e)
edges = list(merged.values())

graph = {
    "generated": str(date.today()),
    "source": {
        "repo": CONFIG["frontend"],
        "commit": subprocess.run(["git", "-C", str(FRONTEND), "log", "-1", "--format=%h %ad", "--date=short"],
                                 capture_output=True, text=True).stdout.strip(),
    },
    "nodes": sorted(nodes.values(), key=lambda n: n["url"]),
    "edges": edges,
}
(OUT / "screen-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
manual_ev = {e.get("evidence", "") for e in manual}
manual_places = {ev.split(":")[0] for ev in manual_ev}
unresolved = [u for u in unresolved
              if not any(place and place in u for place in manual_places)]

(OUT / "unresolved.md").write_text(
    "# What the extractor could not read\n\n"
    "Close each line either by fixing the script or by adding an edge to `edges-manual.json`.\n\n"
    + "\n".join(f"- {u}" for u in unresolved) + "\n",
    encoding="utf-8")

print(f"nodes: {len(nodes)}  edges: {len(edges)} (hand-written: {len(manual)})  unresolved: {len(unresolved)}")
