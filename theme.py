#!/usr/bin/env python3
"""Pull a theme from the juw12/themes library. One file, no dependencies.

    python theme.py list [word]                 every theme, or the ones matching a word
    python theme.py show <id>                   tokens, fonts, contrast, where it came from
    python theme.py pull <id>                   print the CSS
    python theme.py pull <id> --to src/theme.css
    python theme.py pull <id> --format json
    python theme.py pull <id> --design-md       a design.md brief built from the theme

    python theme.py components list [--category backgrounds] [--search text]
    python theme.py components add SplitText [--flavor TS-TW] [--theme <id>] [--run]

The second shelf is a catalogue of the free React Bits components (https://reactbits.dev, by David Haz,
MIT + Commons Clause). No component source is kept in this library: "add" prints the command that pulls
the component straight from reactbits.dev into the app, and --run runs it in the current folder.

It reads the themes/ folder next to this file first, then falls back to GitHub.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request

RAW = "https://raw.githubusercontent.com/juw12/themes/main/"
HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(relative, local_only=False):
    """Return (text, where). Local file wins; GitHub is the fallback."""
    local = os.path.join(HERE, *relative.split("/"))
    if os.path.exists(local):
        with open(local, encoding="utf-8") as handle:
            return handle.read(), local
    if local_only:
        raise SystemExit(f"not found locally: {relative}")
    try:
        with urllib.request.urlopen(RAW + relative, timeout=20) as response:
            return response.read().decode("utf-8"), RAW + relative
    except Exception as error:  # network, proxy, 404
        raise SystemExit(f"could not read {relative} here or from {RAW + relative}: {error}")


def index():
    text, _ = fetch("themes.json")
    return json.loads(text)["themes"]


def resolve(wanted):
    """Accept an id, a name, or a unique part of either."""
    themes = index()
    key = wanted.strip().lower().replace(" ", "-")
    for theme in themes:
        if key in (theme["id"], theme["name"].lower().replace(" ", "-")):
            return theme
    hits = [t for t in themes if key in t["id"] or key in " ".join(t["projects"]).lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f'no theme matches "{wanted}". Try: python theme.py list')
    names = ", ".join(t["id"] for t in hits)
    raise SystemExit(f'"{wanted}" matches several themes: {names}')


def cmd_list(args):
    word = (args.word or "").lower()
    rows = []
    for theme in index():
        haystack = " ".join(
            [theme["id"], theme["name"], theme["scheme"], theme["hue"], theme["display"], theme["body"]]
            + theme["projects"]
        ).lower()
        if word and word not in haystack:
            continue
        ground = theme["scheme"] + ("+dark" if theme["has_dark"] else "")
        rows.append((theme["id"], theme["name"], ground, theme["bg"], theme["accent"], theme["display"]))
    if not rows:
        print("no theme matches")
        return
    width = max(len(row[0]) for row in rows)
    name_width = max(len(row[1]) for row in rows)
    for row in rows:
        print(f"{row[0]:<{width}}  {row[1]:<{name_width}}  {row[2]:<10}  bg {row[3]}  accent {row[4]}  {row[5]}")
    print(f"{len(rows)} themes")


def load_theme(wanted):
    entry = resolve(wanted)
    text, _ = fetch(entry["json"])
    return json.loads(text)


def cmd_show(args):
    theme = load_theme(args.id)
    print(f"{theme['name']}  ({theme['id']})")
    print(theme["note"])
    print(theme["summary"])
    print("from: " + ", ".join(p["repo"] for p in theme["projects"]) + f"  [{theme['source']}, checked {theme['checked']}]")
    print()
    for role, value in theme["colors"].items():
        print(f"  --{role.replace('_', '-'):<12} {value}   {theme['origin']['light'].get(role, '')}")
    if theme["dark"]:
        print("  dark set:")
        for role, value in theme["dark"].items():
            print(f"  --{role.replace('_', '-'):<12} {value}")
    print()
    for key in ("display", "body", "mono"):
        print(f"  --font-{key:<8} {theme['fonts'][key]}")
    print(f"  --radius       {theme['radius']}")
    if theme["fonts"]["web_url"]:
        print(f"  web fonts      {theme['fonts']['web_url']}")
    print()
    for key, value in theme["contrast"]["light"].items():
        print(f"  {key.replace('_', ' '):<22} {value}:1")
    for line in theme["warnings"]:
        print("  note: " + line)


def design_md(theme):
    colours = theme["colors"]
    rows = "\n".join(
        f"| `--{role.replace('_', '-')}` | `{value}` | {theme['origin']['light'].get(role, '')} |"
        for role, value in colours.items()
    )
    numbers = theme["contrast"]["light"]
    warnings = "\n".join("- " + line for line in theme["warnings"]) or "- none"
    web = theme["fonts"]["web_url"] or "none, system fonts only"
    names = ", ".join(p["repo"] for p in theme["projects"])
    return f"""# Design: {theme['name']}

Theme `{theme['id']}` from https://juw12.github.io/themes/#{theme['id']} (first used in: {names}).

{theme['note']}

## Tokens

| Token | Value | Read from |
|---|---|---|
{rows}

- Display: `{theme['fonts']['display']}`
- Body: `{theme['fonts']['body']}`
- Mono: `{theme['fonts']['mono']}`
- Radius: `{theme['radius']}`
- Web fonts: {web}

## Rules

- Use only these tokens. Do not add a colour that is not in the table; ask first.
- One accent. It marks the one main action on a screen and links. Everything else is ink, muted and line.
- Headings in the display face, text in the body face, numbers and code in mono.
- Corners use `--radius`. Borders use `--line`. Panels use `--surface` on `--bg`.
- No gradients, no glow, no glass, no emoji as icons.

## Contrast (WCAG 2)

- ink on bg {numbers['ink_on_bg']}:1, muted on bg {numbers['muted_on_bg']}:1
- accent on bg {numbers['accent_on_bg']}:1, accent-ink on accent {numbers['accent_ink_on_accent']}:1

Watch out:
{warnings}
"""


def cmd_pull(args):
    entry = resolve(args.id)
    if args.design_md:
        text = design_md(json.loads(fetch(entry["json"])[0]))
    elif args.format == "json":
        text, _ = fetch(entry["json"])
    else:
        text, _ = fetch(entry["css"])
    if args.to:
        folder = os.path.dirname(os.path.abspath(args.to))
        os.makedirs(folder, exist_ok=True)
        with open(args.to, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        print(f"{entry['name']} -> {args.to}")
    else:
        sys.stdout.write(text)


def catalogue():
    text, _ = fetch("reactbits.json")
    return json.loads(text)


def squash(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def find_component(wanted):
    """Accept the component's name, its id or its title, in any case, with or without spaces and dashes."""
    data = catalogue()
    rows = data["components"] + data["unlisted"]
    key = squash(wanted)
    for row in rows:
        if key in (squash(row["name"]), squash(row["id"]), squash(row["title"])):
            return data, row
    hits = [row for row in rows if key and key in squash(row["name"])]
    if len(hits) == 1:
        return data, hits[0]
    if not hits:
        raise SystemExit(f'no component matches "{wanted}". Try: python theme.py components list --search {wanted}')
    names = ", ".join(row["name"] for row in hits[:12])
    raise SystemExit(f'"{wanted}" matches several components: {names}')


def cmd_components_list(args):
    data = catalogue()
    category = squash(args.category or "")
    known = [squash(row["id"]) for row in data["categories"]]
    if category and category not in known:
        raise SystemExit("no such category. Categories: " + ", ".join(row["id"] for row in data["categories"]))
    word = (args.search or "").lower()
    rows = []
    for row in data["components"]:
        if category and squash(row["category"]) != category:
            continue
        haystack = " ".join([row["name"], row["title"], row["category"], row["description"]] + row["dependencies"]).lower()
        if word and word not in haystack:
            continue
        rows.append(row)
    if not rows:
        print("no component matches")
        return
    width = max(len(row["name"]) for row in rows)
    group_width = max(len(row["category"]) for row in rows)
    for row in rows:
        print(f"{row['name']:<{width}}  {row['category']:<{group_width}}  {row['description']}")
    source = data["read_from"]
    print(f"{len(rows)} of {data['count']} components, read from {source['site']} on {source['read']}")


def cmd_components_add(args):
    data, row = find_component(args.name)
    flavor = (args.flavor or data["default_flavor"]).upper()
    if flavor not in row["flavors"]:
        raise SystemExit(f"{row['name']} has no {flavor} flavour. It has: " + ", ".join(row["flavors"]))
    command = data["install"]["shadcn"].format(name=row["name"], flavor=flavor)
    other = data["install"]["jsrepo"].format(name=row["name"], flavor=flavor)
    notes = [f"{row['name']} ({flavor}): {row['description']}"]
    if row.get("demo"):
        notes.append("See it live: " + row["demo"])
    else:
        notes.append("No demo page: " + row.get("why", "it is not in their menu"))
    if row["dependencies"]:
        notes.append("It brings these packages: " + ", ".join(row["dependencies"]))
    if args.theme:
        theme = load_theme(args.theme)
        colours = theme["colors"]
        notes.append(
            f"Colours of {theme['name']} to pass as props where the component takes colours: "
            f"accent {colours['accent']}, bg {colours['bg']}, ink {colours['ink']}"
        )
    origin = data["read_from"]
    notes.append(f"By {origin['author']}, {origin['licence']}. The source is not kept in this library;")
    notes.append("the command below pulls it from reactbits.dev into this app. Or: " + other)
    if not args.execute:
        for line in notes:
            print("# " + line)
        print(command)
        return
    for line in notes:
        print("# " + line, file=sys.stderr)
    words = command.split()[1:]
    for name, lead in (("npx", []), ("bunx", []), ("pnpm", ["dlx"])):  # whichever of these this computer has
        program = shutil.which(name)
        if program:
            break
    else:
        raise SystemExit("npx, bunx and pnpm were not found. Install Node.js or Bun, or run this yourself: " + command)
    print("$ " + " ".join([name] + lead + words), file=sys.stderr)
    raise SystemExit(subprocess.call([program] + lead + words))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Pull a theme from the juw12/themes library.")
    commands = parser.add_subparsers(dest="command", required=True)
    list_parser = commands.add_parser("list", help="list themes")
    list_parser.add_argument("word", nargs="?", help="filter by a word: dark, serif face, project, colour")
    list_parser.set_defaults(run=cmd_list)
    show_parser = commands.add_parser("show", help="show one theme")
    show_parser.add_argument("id")
    show_parser.set_defaults(run=cmd_show)
    pull_parser = commands.add_parser("pull", help="print or save a theme")
    pull_parser.add_argument("id")
    pull_parser.add_argument("--format", choices=["css", "json"], default="css")
    pull_parser.add_argument("--design-md", action="store_true", help="write a design.md brief instead")
    pull_parser.add_argument("--to", help="file to write (default: print)")
    pull_parser.set_defaults(run=cmd_pull)
    components_parser = commands.add_parser("components", help="the React Bits catalogue: list, add")
    component_commands = components_parser.add_subparsers(dest="action", required=True)
    components_list = component_commands.add_parser("list", help="list the components")
    components_list.add_argument("--category", help="text-animations, animations, components, micro, backgrounds")
    components_list.add_argument("--search", help="a word in the name, description or dependencies")
    components_list.set_defaults(run=cmd_components_list)
    components_add = component_commands.add_parser("add", help="print (or run) the command that adds one")
    components_add.add_argument("name")
    components_add.add_argument("--flavor", "--flavour", help="JS-CSS, JS-TW, TS-CSS or TS-TW (default TS-TW)")
    components_add.add_argument("--theme", help="a theme id: also print its colours to pass as props")
    components_add.add_argument("--run", dest="execute", action="store_true", help="run the command in the current folder")
    components_add.set_defaults(run=cmd_components_add)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
