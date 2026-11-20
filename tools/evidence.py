"""Evidence index: every colour that a project really declares or paints.

Used by build.py and check.py so that no colour in the library is invented.
"""
import json
import os
import re

import colors as C

COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?|oklch)\([^()]{3,60}\)"
)


def _norm(token):
    parsed = C.parse_color(token)
    if not parsed:
        return None
    return C.to_hex(parsed)[:7].lower()


def from_text(text):
    found = set()
    for match in COLOR_RE.findall(text):
        value = _norm(match)
        if value:
            found.add(value)
    return found


def _walk(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                found |= from_text(key)
            _walk(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, found)
    elif isinstance(node, str):
        found |= from_text(node)


def load(data_dir):
    """Return {repo: set(hex)} from data/raw/<repo>/* and data/live.json."""
    index = {}
    raw_dir = os.path.join(data_dir, "raw")
    if os.path.isdir(raw_dir):
        for repo in os.listdir(raw_dir):
            found = set()
            folder = os.path.join(raw_dir, repo)
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        found |= from_text(handle.read())
                except OSError:
                    continue
            index[repo] = found
    live_path = os.path.join(data_dir, "live.json")
    if os.path.exists(live_path):
        with open(live_path, encoding="utf-8") as handle:
            live = json.load(handle)
        for repo, record in live.items():
            found = index.setdefault(repo, set())
            _walk(record, found)
    return index
