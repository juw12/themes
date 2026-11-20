"""Run every gate on the library. Exit code 0 only when all gates pass.

    python tools/check.py                 data gates + page gates (needs Playwright for G7 and G8)
    python tools/check.py --no-browser    data gates only
    python tools/check.py --online        also re-check the template repos against the GitHub API (needs gh)

G5 (privacy) reads names that must never appear from data/private_words.txt (one per line, not in git).
"""
import functools
import http.server
import json
import os
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build as B  # noqa: E402

HEX = re.compile(r"^#[0-9a-f]{6}$")
TEXT_EXT = (".py", ".md", ".json", ".css", ".html", ".txt", "LICENSE", ".gitignore")
WIDTHS = [320, 390, 768, 1024, 1440]
MOJIBAKE = ["\u00c3\u00a2", "\u00e2\u20ac", "\u00c3\u00a9", "\ufffd", "\u00c2\u00a0"]
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B06\uFE0F]")
results = []


def gate(name, problems, note=""):
    ok = not problems
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + note) if note else ''}")
    for line in problems[:12]:
        print("      - " + line)
    if len(problems) > 12:
        print(f"      ... and {len(problems) - 12} more")


def load_themes():
    index = B.load_json(os.path.join(ROOT, "themes.json"))
    themes = [B.load_json(os.path.join(ROOT, entry["json"])) for entry in index["themes"]]
    return index, themes


def text_files():
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "data", "shots", "node_modules")]
        for name in files:
            if name.endswith(TEXT_EXT) or name in ("LICENSE", ".nojekyll"):
                yield os.path.join(folder, name)


def g1_schema(themes):
    problems = []
    need = ["schema", "id", "name", "summary", "note", "scheme", "hue", "projects", "source", "checked", "colors",
            "dark", "extras", "fonts", "radius", "contrast", "origin", "derived", "curated", "warnings"]
    for theme in themes:
        for key in need:
            if key not in theme:
                problems.append(f"{theme.get('id')}: missing {key}")
        for label, colours in (("colors", theme["colors"]), ("dark", theme["dark"] or {})):
            if colours:
                for role in B.CORE_ROLES:
                    if role not in colours:
                        problems.append(f"{theme['id']}: {label} has no {role}")
            for role, value in colours.items():
                if role not in B.ROLE_ORDER or not HEX.match(value):
                    problems.append(f"{theme['id']}: {label}.{role} = {value}")
        for key in ("display", "body", "mono"):
            if not theme["fonts"].get(key):
                problems.append(f"{theme['id']}: no {key} font")
        if not theme["projects"]:
            problems.append(f"{theme['id']}: no project")
        if not re.match(r"^[a-z0-9-]+$", theme["id"]):
            problems.append(f"{theme['id']}: bad id")
    gate("G1 schema", problems, f"{len(themes)} themes")


def g2_unique(index, themes):
    problems = []
    ids = [t["id"] for t in themes]
    names = [t["name"] for t in themes]
    if len(set(ids)) != len(ids):
        problems.append("duplicate id")
    if len(set(names)) != len(names):
        problems.append("duplicate name")
    on_disk = sorted(n[:-5] for n in os.listdir(os.path.join(ROOT, "themes")) if n.endswith(".json"))
    css_disk = sorted(n[:-4] for n in os.listdir(os.path.join(ROOT, "themes")) if n.endswith(".css"))
    if on_disk != sorted(ids) or css_disk != sorted(ids):
        problems.append("themes/ folder and themes.json disagree")
    if index["count"] != len(ids):
        problems.append("count in themes.json is wrong")
    gate("G2 unique ids and names, index matches files", problems)


def g3_provenance(themes):
    evidence = B.load_json(os.path.join(ROOT, "src", "evidence.json"))
    problems = []
    checked = 0
    for theme in themes:
        known = set()
        for project in theme["projects"]:
            known |= set(evidence.get(project["repo"], []))
        derived = set(theme["derived"])
        for label, colours, prefix in (("light", theme["colors"], ""), ("dark", theme["dark"] or {}, "dark.")):
            for role, value in colours.items():
                if prefix + role in derived:
                    if not theme["origin"][label][role].startswith("derived"):
                        problems.append(f"{theme['id']}: {label}.{role} is derived but not labelled")
                    continue
                checked += 1
                if value not in known:
                    problems.append(f"{theme['id']}: {label}.{role} {value} not found in the project")
        for name, value in theme["extras"].items():
            checked += 1
            if value not in known:
                problems.append(f"{theme['id']}: extra {name} {value} not found in the project")
    gate("G3 every colour is in the project's CSS or page, or labelled derived", problems, f"{checked} colours traced")


def g4_contrast(themes):
    problems = []
    for theme in themes:
        for label, colours in (("light", theme["colors"]), ("dark", theme["dark"])):
            if not colours:
                continue
            fresh = B.measure(colours)
            if fresh != theme["contrast"][label]:
                problems.append(f"{theme['id']}: stored {label} contrast differs from recomputed")
            for key in ("ink_on_bg", "muted_on_bg", "accent_ink_on_accent", "ink_on_surface"):
                if fresh[key] < 4.5 and not any(str(fresh[key]) in w for w in theme["warnings"]):
                    problems.append(f"{theme['id']}: {label} {key} {fresh[key]} has no warning")
        if theme["contrast"]["light"]["ink_on_bg"] < 7:
            problems.append(f"{theme['id']}: ink on bg under 7:1")
    gate("G4 contrast recomputed, low values carry a warning, ink on bg at least 7:1", problems)


def g5_privacy():
    words_file = os.path.join(ROOT, "data", "private_words.txt")
    if not os.path.exists(words_file):
        gate("G5 privacy", ["data/private_words.txt is missing, so this gate could not run"])
        return
    with open(words_file, encoding="utf-8") as handle:
        words = [line.strip().lower() for line in handle if line.strip() and not line.startswith("#")]
    problems = []
    for path in text_files():
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read().lower()
        for word in words:
            if re.search(r"(?<![a-z0-9-])" + re.escape(word) + r"(?![a-z0-9-])", text):
                problems.append(f"{os.path.relpath(path, ROOT)}: contains a private word (entry {words.index(word) + 1})")
    gate("G5 no private project names or personal paths in public files", problems, f"{len(words)} words")


def g6_hygiene():
    problems = []
    count = 0
    for path in text_files():
        count += 1
        with open(path, "rb") as handle:
            raw = handle.read()
        rel = os.path.relpath(path, ROOT)
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{rel}: BOM")
        if b"\r" in raw:
            problems.append(f"{rel}: CR line endings")
        text = raw.decode("utf-8", errors="replace")
        if any(mark in text for mark in MOJIBAKE):
            problems.append(f"{rel}: mojibake")
        if rel.replace("\\", "/") != "tools/check.py" and (EMOJI.search(text) or "\u2014" in text):
            problems.append(f"{rel}: emoji or em dash")
    gate("G6 text hygiene: UTF-8, LF, no mojibake, no emoji, no em dash", problems, f"{count} files")


def g9_cli(index, themes):
    problems = []

    def run(*args):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "theme.py"), *args], capture_output=True)
        return out.returncode, out.stdout.decode("utf-8").replace("\r\n", "\n")

    code, listing = run("list")
    if code != 0 or f"{len(themes)} themes" not in listing:
        problems.append("theme.py list does not report every theme")
    for theme in (themes[0], themes[len(themes) // 2], themes[-1]):
        with open(os.path.join(ROOT, "themes", theme["id"] + ".css"), encoding="utf-8") as handle:
            want = handle.read()
        code, got = run("pull", theme["id"])
        if code != 0 or got != want:
            problems.append(f"theme.py pull {theme['id']} differs from the file")
        code, got = run("pull", theme["name"], "--design-md")
        if code != 0 or theme["colors"]["accent"] not in got:
            problems.append(f"theme.py pull --design-md failed for {theme['name']}")
    gate("G9 theme.py list / pull / --design-md", problems)


def g10_templates():
    templates = B.load_json(os.path.join(ROOT, "src", "templates.json"))
    problems = []
    count = 0
    for group in templates["groups"]:
        for row in group["repos"]:
            count += 1
            out = subprocess.run(["gh", "api", "repos/" + row["repo"]], capture_output=True)
            if out.returncode != 0:
                problems.append(f"{row['repo']}: not reachable")
                continue
            info = json.loads(out.stdout.decode("utf-8"))
            if info.get("archived"):
                problems.append(f"{row['repo']}: archived")
            if info["full_name"].lower() != row["repo"].lower():
                problems.append(f"{row['repo']}: now lives at {info['full_name']}")
            drift = abs(info["stargazers_count"] - row["stars"])
            if drift > max(50, row["stars"] * 0.02):
                problems.append(f"{row['repo']}: stars {row['stars']} vs live {info['stargazers_count']}")
    gate("G10 template repos exist, are not archived, stars match the API", problems, f"{count} repos")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(Quiet, directory=ROOT)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


def browser_gates(index, themes):
    from playwright.sync_api import sync_playwright

    base = serve()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        # G7: the gallery page
        problems = []
        errors = []
        for width in WIDTHS:
            context = browser.new_context(viewport={"width": width, "height": 900})
            context.route(re.compile(r"fonts\.(googleapis|gstatic)\.com"), lambda route: route.abort())
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text)
                    if message.type == "error" and "ERR_FAILED" not in message.text and "fonts." not in message.text
                    else None)
            page.goto(base + "index.html", wait_until="load")
            for worn in ("", "vale-shardlight"):
                if worn:
                    page.evaluate("id => document.querySelector(`[data-wear='${id}']`).click()", worn)
                over = page.evaluate(
                    """() => {
                        const limit = document.documentElement.clientWidth;
                        const wide = [];
                        if (document.documentElement.scrollWidth > limit + 1) wide.push('page');
                        document.querySelectorAll('.card, .cmd, .repos, .starter, .bar-in').forEach((el) => {
                            const box = el.getBoundingClientRect();
                            if (box.right > limit + 1 || box.left < -1) wide.push(el.className + ' ' + (el.id || ''));
                        });
                        document.querySelectorAll('.card *').forEach((el) => {
                            const card = el.closest('.card').getBoundingClientRect();
                            const box = el.getBoundingClientRect();
                            if (box.width && box.right > card.right + 1) wide.push('inside ' + el.closest('.card').id + ' ' + el.tagName);
                        });
                        return wide.slice(0, 5);
                    }"""
                )
                if over:
                    problems.append(f"{width}px{' worn' if worn else ''}: overflow in {over}")
                tight = page.evaluate(
                    """() => [...document.querySelectorAll('h1, h2, h3, p, table, .cmd')].filter((el) => {
                        const box = el.getBoundingClientRect();
                        return box.width && (box.left < 15 || box.right > document.documentElement.clientWidth - 15);
                    }).map((el) => el.tagName + ':' + el.textContent.trim().slice(0, 24)).slice(0, 4)"""
                )
                if tight:
                    problems.append(f"{width}px: text touches the screen edge: {tight}")
            if width == 1440:
                cards = page.locator(".card").count()
                if cards != len(themes):
                    problems.append(f"{cards} cards on the page, {len(themes)} themes in themes.json")
                page.evaluate("() => document.querySelector(\"[data-copy-css='vow-brick']\").click()")
                page.wait_for_timeout(200)
                copied = page.evaluate("() => window.__lastCopied || ''")
                with open(os.path.join(ROOT, "themes", "vow-brick.css"), encoding="utf-8") as handle:
                    if copied != handle.read():
                        problems.append("Copy CSS does not give the exact file")
                worn_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
                want = B.rgb(next(t for t in themes if t["id"] == "vale-shardlight")["colors"]["bg"])
                if worn_bg.replace(" ", "") != "rgb(%d,%d,%d)" % tuple(want[:3]):
                    problems.append(f"Wear it did not change the page ground ({worn_bg})")
                page.fill("#search", "georgia")
                shown = page.evaluate("() => document.querySelectorAll('.card:not([hidden])').length")
                expect = sum(1 for t in themes if "georgia" in " ".join(
                    [B.first_family(t["fonts"][k]) for k in ("display", "body", "mono")]).lower()
                    or "georgia" in t["name"].lower())
                if shown != expect:
                    problems.append(f"search 'georgia' shows {shown}, expected {expect}")
                page.fill("#search", "")
                page.click(".pill[data-value='dark']")
                shown = page.evaluate("() => document.querySelectorAll('.card:not([hidden])').length")
                if shown != sum(1 for t in themes if t["scheme"] == "dark"):
                    problems.append("Dark filter count is wrong")
                small = page.evaluate(
                    """() => [...document.querySelectorAll('button, .link, summary')].filter((el) => {
                        const box = el.getBoundingClientRect();
                        return box.width && box.height < 26;
                    }).length"""
                )
                if small:
                    problems.append(f"{small} controls are under 26px tall")
            context.close()
        problems += ["console: " + text for text in sorted(set(errors))]
        gate("G7 page: no overflow at 320 to 1440px, no errors, card count, copy, wear, filters", problems)

        # G7b: starter
        problems = []
        for width in (320, 1024):
            page = browser.new_page(viewport={"width": width, "height": 800})
            page.route(re.compile(r"fonts\.(googleapis|gstatic)\.com"), lambda route: route.abort())
            page.goto(base + "starter/index.html?theme=riak-tidepool", wait_until="networkidle")
            wide = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if wide > 1:
                problems.append(f"starter overflows by {wide}px at {width}px")
            accent = page.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()")
            want = next(t for t in themes if t["id"] == "riak-tidepool")["colors"]["accent"]
            if accent != want:
                problems.append(f"starter ?theme= did not load the theme ({accent})")
            page.close()
        gate("G7b starter: no overflow, ?theme= swaps the tokens", problems)

        # G8: each CSS file, loaded in a browser, gives the JSON values
        problems = []
        page = browser.new_page()
        for theme in themes:
            for scheme in (["light", "dark"] if theme["dark"] else ["light"]):
                page.emulate_media(color_scheme=scheme)
                page.goto(base + "tools/blank.html?css=" + theme["id"], wait_until="load")
                want = dict(theme["dark"] if scheme == "dark" else theme["colors"])
                got = page.evaluate(
                    """(roles) => {
                        const style = getComputedStyle(document.documentElement);
                        const out = {};
                        roles.forEach((role) => { out[role] = style.getPropertyValue('--' + role.replace('_', '-')).trim(); });
                        out.radius = style.getPropertyValue('--radius').trim();
                        out.display = style.getPropertyValue('--font-display').trim();
                        return out;
                    }""",
                    list(want),
                )
                for role, value in want.items():
                    if got[role] != value:
                        problems.append(f"{theme['id']} {scheme}: --{role} is {got[role]}, JSON says {value}")
                if got["radius"] != theme["radius"] or got["display"] != theme["fonts"]["display"]:
                    problems.append(f"{theme['id']} {scheme}: radius or display font differs")
        gate("G8 every themes/<id>.css gives the JSON values in a browser, light and dark", problems)


def main():
    index, themes = load_themes()
    g1_schema(themes)
    g2_unique(index, themes)
    g3_provenance(themes)
    g4_contrast(themes)
    g5_privacy()
    g6_hygiene()
    g9_cli(index, themes)
    if "--online" in sys.argv:
        g10_templates()
    if "--no-browser" not in sys.argv:
        browser_gates(index, themes)
    passed = sum(1 for _, ok in results if ok)
    print(f"GATES {passed}/{len(results)}", flush=True)
    sys.stdout.flush()
    os._exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
