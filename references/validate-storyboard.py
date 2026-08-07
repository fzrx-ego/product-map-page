#!/usr/bin/env python3
"""Check a storyboard folder before delivery.

Usage:
    python3 validate-storyboard.py <map_dir>/storyboard

Problems (exit code 1):
  1. HTML markup — unclosed and stray tags.
  2. Images — every src exists on disk.
  3. Links — the target file exists and the anchor is present on it.
  4. Markdown backticks left inside HTML (should be <code>).
  5. External resources (CDN, web fonts) — the pages are opened from disk, offline.
  6. Orphaned frames — a PNG shown on no page.
  7. Duplicate frames — byte-identical PNGs.
  8. Boilerplate — the same "How it differs" text repeated across blocks of one page.

Notes (printed, do not fail the run):
  - a frame with no capture JSON beside it;
  - a frame captured on a redirected URL, or with failed requests or console errors — make sure
    the page file says so instead of recording the screen as empty.

Maps written in another language: add that language's wording to DIFFERENCE_HEADINGS.
"""

import glob
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser

VOID = {"meta", "link", "img", "br", "hr", "input", "source", "col"}
BOILERPLATE_LIMIT = 3  # the same explanation in this many blocks is a template, not an explanation
DIFFERENCE_HEADINGS = ("how it differs", "difference")


def plain(fragment: str) -> str:
    """Text with tags and repeated whitespace removed."""
    return re.sub(r"<[^>]+>|\s+", " ", fragment).strip()


class Balance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"</{tag}> while {self.stack[-3:]} are open")


def check(root: str) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    notes: list[str] = []
    pages = sorted(glob.glob(os.path.join(root, "*.html")))
    if not pages:
        return [f"no pages found in {root}"], notes

    anchors = {
        os.path.basename(p): set(re.findall(r'id="([^"]+)"', open(p, encoding="utf-8").read()))
        for p in pages
    }

    used_images: set[str] = set()
    for page in pages:
        name = os.path.basename(page)
        text = open(page, encoding="utf-8").read()

        balance = Balance()
        balance.feed(text)
        if balance.errors or balance.stack:
            problems.append(
                f"{name}: markup — {balance.errors[:3]}, unclosed {balance.stack[:3]}"
            )

        if "`" in text:
            problems.append(f"{name}: markdown backticks ({text.count('`')}) instead of <code>")

        # <a href> pointing outwards is fine; only loaded resources break an offline page
        loaded = re.findall(r'@import\s+url\(\s*[\'"]?(https?://[^\'")]+)', text)
        loaded += re.findall(r'<(?:script|img|iframe)[^>]+src="(https?://[^"]+)"', text)
        loaded += re.findall(r'<link[^>]+href="(https?://[^"]+)"', text)
        for external in loaded:
            problems.append(f"{name}: external resource {external}")

        for src in re.findall(r'<img[^>]+src="([^"]+)"', text):
            if src.startswith("data:"):
                continue  # inline image, nothing to resolve on disk
            path = os.path.join(root, src)
            used_images.add(os.path.normpath(path))
            if not os.path.exists(path):
                problems.append(f"{name}: missing image {src[:120]}")

        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http", "mailto:", "data:")):
                continue
            path, _, fragment = href.partition("#")
            target = path or name
            if path and not os.path.exists(os.path.join(root, path)):
                problems.append(f"{name}: missing file {path}")
                continue
            if fragment and target in anchors and fragment not in anchors[target]:
                problems.append(f"{name}: anchor {href} not found")

        # only "How it differs" is checked for boilerplate: procedural blocks and an identical
        # set of fields may legitimately repeat between neighbouring states — a difference may not
        pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", text, re.S)
        differences = Counter(
            plain(body)
            for title, body in pairs
            if any(h in plain(title).lower() for h in DIFFERENCE_HEADINGS)
        )
        for body, count in differences.items():
            if count >= BOILERPLATE_LIMIT and len(body) > 40:
                problems.append(
                    f'{name}: "How it differs" repeated verbatim {count} times — "{body[:70]}…"'
                )

    frames = sorted(glob.glob(os.path.join(root, "assets", "*", "*.png")))

    for png in frames:
        if os.path.normpath(png) not in used_images:
            problems.append(f"orphaned frame {os.path.relpath(png, root)}")

    digests = defaultdict(list)
    for png in frames:
        digests[hashlib.md5(open(png, "rb").read()).hexdigest()].append(
            os.path.relpath(png, root)
        )
    for files in digests.values():
        if len(files) > 1:
            problems.append("identical frames: " + ", ".join(files))

    # the capture record the harness writes next to every frame
    for png in frames:
        rel = os.path.relpath(png, root)
        sidecar = png[:-4] + ".json"
        if not os.path.exists(sidecar):
            notes.append(f"{rel}: no capture JSON beside the frame")
            continue
        try:
            data = json.load(open(sidecar, encoding="utf-8"))
        except json.JSONDecodeError as err:
            problems.append(f"{os.path.relpath(sidecar, root)}: unreadable ({err})")
            continue
        if data.get("redirected"):
            notes.append(f"{rel}: captured after a redirect to {data.get('url')}")
        for field in ("failedRequests", "consoleErrors"):
            if data.get(field):
                notes.append(f"{rel}: {len(data[field])} {field} during capture — {data[field][0][:90]}")

    return problems, notes


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems, notes = check(root)
    for item in notes:
        print(" ?", item)
    if problems:
        print(f"problems: {len(problems)}")
        for item in problems:
            print(" -", item)
        return 1
    pages = len(glob.glob(os.path.join(root, "*.html")))
    frames = len(glob.glob(os.path.join(root, "assets", "*", "*.png")))
    print(f"checks passed: {pages} pages, {frames} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
