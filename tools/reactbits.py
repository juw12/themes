"""Read the free React Bits components and write a catalogue of them. No source is copied.

    python tools/reactbits.py            read reactbits.dev, write src/reactbits.json and reactbits.json
    python tools/reactbits.py --links    also ask for every demo page and every install file (about 440 requests)

React Bits (https://reactbits.dev, by David Haz) is MIT + Commons Clause: using a component in an app is
allowed, redistributing the components is not. So this file keeps facts only: name, category, description,
dependencies, the demo page and the install command. The "files" field of their registry, which holds the
component source, is dropped here and never written. Sounds are left out.

A component reaches an app when it is pulled, straight from reactbits.dev (theme.py components add).
"""
import concurrent.futures
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build as B  # noqa: E402

SITE = "https://reactbits.dev"
REPO = "DavidHDev/react-bits"
REGISTRY_URL = SITE + "/r/registry.json"
COMMIT_URL = "https://api.github.com/repos/" + REPO + "/commits/main"
CATEGORIES_URL = "https://raw.githubusercontent.com/" + REPO + "/{ref}/src/constants/Categories.js"
LICENSE_URL = "https://github.com/" + REPO + "/blob/main/LICENSE.md"
FLAVORS = ["JS-CSS", "JS-TW", "TS-CSS", "TS-TW"]
DEFAULT_FLAVOR = "TS-TW"
NOT_COMPONENTS = ["Get Started"]
SOURCE_FILE = os.path.join(ROOT, "src", "reactbits.json")
PUBLIC_FILE = os.path.join(ROOT, "reactbits.json")
AGENT = "juw12-themes-catalogue (+https://github.com/juw12/themes)"
FLAVOR_END = re.compile(r"-(JS|TS)-(CSS|TW)$")


def get(url, timeout=40):
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def status(url, timeout=30):
    """The HTTP status of a page, 0 when nothing answered."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "*/*"})
    for _ in range(2):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read(1)
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except Exception:
            continue
    return 0


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def squash(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def plain(text):
    """One line, ASCII punctuation: the library's own text rules (no em dash, no curly quotes)."""
    swaps = {"\u2014": ", ", "\u2013": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "..."}
    for old, new in swaps.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def parse_categories(text):
    """[(group name, [component display names])] from their sidebar file, in their order."""
    groups = []
    for block in re.finditer(r"name:\s*(['\"])(.+?)\1,\s*subcategories:\s*\[(.*?)\]", text, flags=re.S):
        names = [single or double for single, double in re.findall(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", block.group(3))]
        groups.append((block.group(2), names))
    return groups


def build(registry, categories_text, commit, read_on):
    """The catalogue and the account of what was read. Nothing of an item's "files" is looked at."""
    flavors_of = {}
    facts = {}
    sounds = 0
    other = []
    for item in registry["items"]:
        name = item["name"]
        match = FLAVOR_END.search(name)
        if match:
            base = name[: match.start()]
            flavors_of.setdefault(base, []).append(match.group(1) + "-" + match.group(2))
            facts.setdefault(base, {})[match.group(1) + "-" + match.group(2)] = item
        elif name.startswith("Sound"):
            sounds += 1
        else:
            other.append(name)

    by_squash = {squash(base): base for base in flavors_of}
    groups = [(name, names) for name, names in parse_categories(categories_text) if name not in NOT_COMPONENTS]
    components = []
    listed = set()
    not_in_registry = []
    for group_name, names in groups:
        for title in names:
            base = by_squash.get(squash(title))
            if not base:
                not_in_registry.append(group_name + " / " + title)
                continue
            listed.add(base)
            components.append(entry(base, facts[base], flavors_of[base], group_name, title))

    unlisted = []
    for base in sorted(set(flavors_of) - listed):
        row = entry(base, facts[base], flavors_of[base], "", base)
        row.pop("category")
        row.pop("demo")
        row["why"] = "in their registry, not in their site's menu, so it has no demo page"
        unlisted.append(row)

    categories = [
        {"id": slug(name), "name": name, "count": sum(1 for row in components if row["category"] == slug(name))}
        for name, _ in groups
    ]
    catalogue = {
        "schema": 1,
        "about": "A catalogue of the free React Bits components. Facts only: no component source is kept here.",
        "read_from": {
            "site": SITE,
            "repo": "https://github.com/" + REPO,
            "commit": commit,
            "read": read_on,
            "author": "David Haz",
            "licence": "MIT + Commons Clause",
            "licence_url": LICENSE_URL,
        },
        "install": {
            "shadcn": "npx shadcn@latest add " + SITE + "/r/{name}-{flavor}.json",
            "shadcn_named": "npx shadcn@latest add @react-bits/{name}-{flavor}",
            "shadcn_named_needs": {"registries": {"@react-bits": SITE + "/r/{name}.json"}},
            "jsrepo": "npx jsrepo@latest add " + SITE + "/r/{name}-{flavor}",
        },
        "flavors": FLAVORS,
        "default_flavor": DEFAULT_FLAVOR,
        "count": len(components),
        "categories": categories,
        "components": components,
        "unlisted": unlisted,
    }
    read = {
        "registry_items": len(registry["items"]),
        "registry_component_names": len(flavors_of),
        "registry_sound_items": sounds,
        "registry_other_items": sorted(other),
        "menu_components": sum(len(names) for _, names in groups),
        "menu_per_category": {slug(name): len(names) for name, names in groups},
        "menu_names_not_in_registry": not_in_registry,
        "catalogue_components": len(components),
        "unlisted": [row["name"] for row in unlisted],
    }
    return catalogue, read


def entry(base, by_flavor, flavors, group_name, title):
    main = by_flavor.get(DEFAULT_FLAVOR) or by_flavor[sorted(by_flavor)[0]]
    return {
        "id": slug(title),
        "name": base,
        "title": title,
        "category": slug(group_name),
        "description": plain(main.get("description") or ""),
        "dependencies": sorted({dep for item in by_flavor.values() for dep in (item.get("dependencies") or [])}),
        "demo": SITE + "/" + slug(group_name) + "/" + slug(title),
        "flavors": [flavor for flavor in FLAVORS if flavor in flavors],
    }


def install_file(name, flavor=DEFAULT_FLAVOR):
    return SITE + "/r/" + name + "-" + flavor + ".json"


def check_links(catalogue, workers=8):
    """Ask for every demo page and every install file. Returns (asked, [problem lines])."""
    urls = [row["demo"] for row in catalogue["components"]]
    urls += [install_file(row["name"]) for row in catalogue["components"] + catalogue["unlisted"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        codes = list(pool.map(status, urls))
    return len(urls), [f"{url} answered {code}" for url, code in zip(urls, codes) if code != 200]


def read_site():
    registry = json.loads(get(REGISTRY_URL))
    try:
        commit = json.loads(get(COMMIT_URL))["sha"]
    except Exception:
        commit = ""
    categories_text = get(CATEGORIES_URL.format(ref=commit or "main"))
    return registry, categories_text, commit


def write(catalogue, read):
    record = {"read": read, "catalogue": catalogue}
    B.write(SOURCE_FILE, json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    B.write(PUBLIC_FILE, json.dumps(catalogue, indent=1, ensure_ascii=False) + "\n")


def main():
    registry, categories_text, commit = read_site()
    catalogue, read = build(registry, categories_text, commit, datetime.date.today().isoformat())
    write(catalogue, read)
    per = ", ".join(f"{row['name']} {row['count']}" for row in catalogue["categories"])
    print(f"wrote reactbits.json: {catalogue['count']} components ({per})")
    print(f"registry: {read['registry_items']} items, {read['registry_component_names']} component names, "
          f"{read['registry_sound_items']} sounds left out; unlisted: {', '.join(read['unlisted']) or 'none'}")
    if read["menu_names_not_in_registry"]:
        print("in their menu but not in the registry: " + ", ".join(read["menu_names_not_in_registry"]))
    if "--links" in sys.argv:
        asked, problems = check_links(catalogue)
        print(f"links: {asked - len(problems)} of {asked} answered 200")
        for line in problems:
            print("  " + line)
        if problems:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
