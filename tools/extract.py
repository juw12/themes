"""Turn the scanned CSS / HTML of each project into one normalised theme record.

Reads data/scan.json + data/raw/. Writes data/extracted.json and prints one review line per repo.
Roles: bg, surface, ink, muted, line, accent, accent2, ok, warn, bad (+ a dark set when the project has one).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from colors import contrast, hue_sat, luminance, over, parse_color, to_hex  # noqa: E402

RAW_DIR = Path("data/raw")

ROLE_NAMES = {
    "bg": "bg background paper page canvas base bg-page page-bg bg0 bg-0 bg1 bg-1 body cream sand app-bg "
    "bg-app body-bg bg-body backdrop ground bg-base base-bg surface-0 shell".split(),
    "surface": "surface card panel bg-card card-bg bg2 bg-2 elev raised sheet tile paper-2 paper2 surface-1 "
    "bg-elev bg-soft white bg-panel panel-bg surface1 bg-raised bg-surface box cardbg card-2 paper-raised "
    "bg-alt alt surface-2 bg3".split(),
    "ink": "ink text fg foreground text-primary ink-1 txt body-text text-1 fg-1 ink0 text-main color-text "
    "text-strong ink-strong fg0 text0 text-color font heading".split(),
    "muted": "muted ink-2 ink2 text-2 text2 text-muted dim subtle sub soft mute ink-soft ink-light "
    "text-secondary fg-2 fg-muted secondary grey gray ink-3 faint text-dim text-soft ink-muted muted-fg "
    "text-light fg-dim ink-mute text-sub meta ink-dim".split(),
    "line": "line border rule hairline stroke divider line-1 border-1 edge outline sep border-color "
    "line-soft border-soft rules border-light line-2 hair bd".split(),
    "accent": "accent primary brand signal main hl highlight link accent-1 key tint cta theme acc "
    "color-accent brand-1 primary-1 accent1 hot pop".split(),
    "accent2": "accent-2 accent2 secondary-accent second accent-alt alt-accent brand-2 teal gold".split(),
    "ok": "ok good success green pos positive win up productive".split(),
    "warn": "warn warning amber caution yellow".split(),
    "bad": "bad danger error red neg negative lose down distracting".split(),
}
FONT_VAR = re.compile(r"font|serif|sans|mono|display|type-|heading|body-face|face", re.IGNORECASE)
RADIUS_VAR = re.compile(r"^(radius|r|rad|round|corner|br)(-|$)|radius", re.IGNORECASE)
GENERIC_FAMILIES = {
    "serif",
    "sans-serif",
    "monospace",
    "system-ui",
    "ui-sans-serif",
    "ui-serif",
    "ui-monospace",
    "-apple-system",
    "blinkmacsystemfont",
    "inherit",
    "cursive",
}
MONO_HINT = re.compile(r"mono|courier|consolas|menlo|code|cascadia", re.IGNORECASE)


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.DOTALL)


def css_from_html(html: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, flags=re.DOTALL | re.IGNORECASE))


def walk_blocks(css: str):
    """Yield (context, declarations) for every block; context joins the enclosing preludes."""
    stack: list[str] = []
    buffer = ""
    for char in css:
        if char == "{":
            stack.append(buffer.strip())
            buffer = ""
        elif char == "}":
            if stack:
                yield " >> ".join(stack), buffer
                stack.pop()
            buffer = ""
        elif char == ";" and stack:
            yield " >> ".join(stack), buffer
            buffer = ""
        else:
            buffer += char


def classify(context: str) -> str:
    lowered = context.lower()
    if "@keyframes" in lowered or "@font-face" in lowered:
        return "skip"
    if "prefers-color-scheme: light" in lowered or "prefers-color-scheme:light" in lowered:
        return "light"
    theme = re.search(r"data-(?:theme|mode|scheme|skin)\s*=\s*[\"']?([\w-]+)", lowered)
    if theme:
        name = theme.group(1)
        if name == "light":
            return "light"
        if name == "dark":
            return "dark"
        return "variant:" + name
    if re.search(r"prefers-color-scheme:\s*dark|[.\[]dark\b|\bdark-mode\b|theme-dark|\.night\b", lowered):
        return "dark"
    if re.search(r"[.\[]light\b|theme-light", lowered):
        return "light"
    if "@media print" in lowered:
        return "skip"
    return "base"


def split_light_dark(value: str, want_dark: bool) -> str:
    match = re.search(r"light-dark\(", value)
    while match:
        start = match.end()
        level = 1
        comma = None
        index = start
        while index < len(value) and level:
            char = value[index]
            if char == "(":
                level += 1
            elif char == ")":
                level -= 1
            elif char == "," and level == 1 and comma is None:
                comma = index
            index += 1
        if comma is None:
            break
        light_part = value[start:comma].strip()
        dark_part = value[comma + 1 : index - 1].strip()
        value = value[: match.start()] + (dark_part if want_dark else light_part) + value[index:]
        match = re.search(r"light-dark\(", value)
    return value


def resolve(value: str, variables: dict, depth: int = 0) -> str:
    if depth > 6:
        return value

    def substitute(match: re.Match) -> str:
        name = match.group(1)
        fallback = match.group(2)
        if name in variables:
            return resolve(variables[name], variables, depth + 1)
        return fallback.strip() if fallback else match.group(0)

    return re.sub(r"var\(\s*--([\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)", substitute, value)


def normalise_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"^(color|colour|clr|c|col|theme|app|ui)-", "", name)
    name = re.sub(r"-(color|colour|default|base|500)$", "", name)
    return name


def first_family(stack: str) -> str:
    for family in stack.split(","):
        clean = family.strip().strip("\"'")
        if clean and clean.lower() not in GENERIC_FAMILIES and not clean.startswith("var("):
            return clean
    return stack.split(",")[0].strip().strip("\"'") if stack else ""


def extract_repo(record: dict) -> dict:
    repo = record["repo"]
    css_parts = []
    google_fonts: list[str] = []
    font_faces: list[str] = []
    has_design_doc = False
    for path in record["files"]:
        raw_file = RAW_DIR / repo / path.replace("/", "__")
        if not raw_file.exists():
            continue
        text = raw_file.read_text(encoding="utf-8", errors="replace")
        lowered = path.lower()
        if lowered.endswith(".md"):
            has_design_doc = True
            continue
        if lowered.endswith(".html"):
            for families in re.findall(r"fonts\.googleapis\.com/css2?\?([^\"'>\s]+)", text):
                for family in re.findall(r"family=([^&:]+)", families):
                    google_fonts.append(family.replace("+", " "))
            css_parts.append(css_from_html(text))
        else:
            css_parts.append(text)
    css = strip_comments("\n".join(css_parts))
    font_faces = list(dict.fromkeys(re.findall(r"@font-face\s*{[^}]*?font-family:\s*[\"']?([^;\"'}]+)", css)))

    modes: dict[str, dict[str, str]] = {"base": {}, "light": {}, "dark": {}}
    variants: dict[str, dict[str, str]] = {}
    body_rule: dict[str, str] = {}
    dark_body_rule: dict[str, str] = {}
    heading_fonts: Counter = Counter()
    body_fonts: Counter = Counter()
    mono_fonts: Counter = Counter()
    all_fonts: Counter = Counter()
    radii: Counter = Counter()
    color_use: Counter = Counter()

    for context, declaration in walk_blocks(css):
        if ":" not in declaration:
            continue
        prop, _, value = declaration.partition(":")
        prop = prop.strip().lower()
        value = value.strip()
        if not prop or not value or len(value) > 400:
            continue
        mode = classify(context)
        if mode == "skip":
            continue
        selector = context.split(" >> ")[-1].lower()

        if prop.startswith("--"):
            name = prop[2:]
            if mode.startswith("variant:"):
                variants.setdefault(mode[8:], {}).setdefault(name, value)
            else:
                modes[mode].setdefault(name, value)
            continue

        is_page = bool(re.search(r"(^|[\s,])(body|html|:root)([\s,.:\[]|$)", selector))
        if prop in ("background", "background-color", "color") and is_page:
            target = dark_body_rule if mode == "dark" else body_rule
            target.setdefault(prop.replace("-color", ""), value)
        if prop == "font-family":
            family = value
            all_fonts[family] += 1
            if is_page:
                body_fonts[family] += 1
            if re.search(r"\bh[1-3]\b|title|display|masthead|brand|hero|headline|logo|wordmark", selector):
                heading_fonts[family] += 1
            if re.search(r"\bcode\b|\bpre\b|mono|kbd|\.num|tabular", selector):
                mono_fonts[family] += 1
        if prop == "border-radius" and mode == "base":
            radius_match = re.fullmatch(r"(\d+(?:\.\d+)?)px", value)
            if radius_match and 2 <= float(radius_match.group(1)) <= 40:
                radii[value] += 1
        if mode == "base" and prop in ("color", "background", "background-color", "border-color", "fill"):
            color_use[value] += 1

    light_vars = {}
    for name, value in {**modes["base"], **modes["light"]}.items():
        light_vars[name] = split_light_dark(value, want_dark=False)
    dark_source = {**modes["base"], **modes["dark"]}
    dark_vars = {name: split_light_dark(value, want_dark=True) for name, value in dark_source.items()}
    uses_light_dark = any("light-dark(" in value for value in modes["base"].values())
    has_dark = bool(modes["dark"]) or uses_light_dark

    def roles_from(variables: dict, page_rule: dict) -> tuple[dict, dict]:
        resolved = {name: resolve(value, variables) for name, value in variables.items()}
        colours = {}
        for name, value in resolved.items():
            parsed = parse_color(value)
            if parsed:
                colours[name] = parsed
        roles: dict[str, tuple] = {}
        role_source: dict[str, str] = {}
        for role, names in ROLE_NAMES.items():
            best = None
            for name, parsed in colours.items():
                normal = normalise_name(name)
                if normal in names:
                    rank = names.index(normal)
                    if best is None or rank < best[0]:
                        best = (rank, name, parsed)
            if best:
                roles[role] = best[2]
                role_source[role] = "--" + best[1]

        for prop, role in (("background", "bg"), ("color", "ink")):
            if role not in roles and prop in page_rule:
                candidate = resolve(page_rule[prop], variables).split(" ")[0]
                parsed = parse_color(candidate) or parse_color(resolve(page_rule[prop], variables))
                if parsed:
                    roles[role] = parsed
                    role_source[role] = "body " + prop
        return roles, role_source

    roles, role_source = roles_from(light_vars, body_rule)
    dark_roles, _ = roles_from(dark_vars, dark_body_rule or body_rule) if has_dark else ({}, {})

    def finish(role_map: dict) -> dict:
        if "bg" not in role_map:
            return {}
        background = role_map["bg"][:3]
        return {role: to_hex(over(colour, background)) for role, colour in role_map.items()}

    light_hex = finish(roles)
    dark_hex = finish(dark_roles)

    # Accent fallback: the most used saturated colour in the base rules.
    inferred = []
    if light_hex and "accent" not in light_hex:
        for value, _count in color_use.most_common(40):
            parsed = parse_color(resolve(value, light_vars))
            if parsed and hue_sat(parsed)[1] > 0.35 and 0.2 < hue_sat(parsed)[2] < 0.75:
                light_hex["accent"] = to_hex(parsed)
                role_source["accent"] = "most used saturated colour"
                inferred.append("accent")
                break

    font_vars = {}
    for name, value in light_vars.items():
        if FONT_VAR.search(name) and ("," in value or "'" in value or '"' in value or "serif" in value):
            font_vars[name] = resolve(value, light_vars)

    def pick_font(counter: Counter, hints: str) -> str:
        for name, value in font_vars.items():
            if re.search(hints, name, re.IGNORECASE):
                return value
        if counter:
            return resolve(counter.most_common(1)[0][0], light_vars)
        return ""

    display_stack = pick_font(heading_fonts, r"display|head|serif|title|brand")
    body_stack = pick_font(body_fonts, r"body|sans|text|ui|base|^font$|font-family")
    mono_stack = pick_font(mono_fonts, r"mono|code|num")
    if not body_stack and all_fonts:
        body_stack = resolve(all_fonts.most_common(1)[0][0], light_vars)

    radius_vars = {
        name: resolve(value, light_vars)
        for name, value in light_vars.items()
        if RADIUS_VAR.search(name) and re.search(r"\d", value)
    }
    radius = ""
    for preferred in ("radius", "r", "radius-md", "radius-card", "radius-m", "r-md", "rad"):
        if preferred in radius_vars:
            radius = radius_vars[preferred]
            break
    if not radius and radius_vars:
        radius = next(iter(radius_vars.values()))
    if not radius and radii:
        radius = radii.most_common(1)[0][0]

    scheme = ""
    if light_hex.get("bg"):
        scheme = "dark" if luminance(parse_color(light_hex["bg"])) < 0.2 else "light"

    return {
        "repo": repo,
        "visibility": record["visibility"],
        "archived": record["archived"],
        "homepage": record["homepage"],
        "description": record["description"],
        "pushed": record["pushed"],
        "files": record["files"],
        "has_design_doc": has_design_doc,
        "var_count": len(light_vars),
        "default_scheme": scheme,
        "light": light_hex,
        "dark": dark_hex,
        "role_source": role_source,
        "inferred": inferred,
        "variants": sorted(variants),
        "fonts": {
            "display": display_stack,
            "body": body_stack,
            "mono": mono_stack,
            "google": list(dict.fromkeys(google_fonts)),
            "faces": font_faces[:6],
        },
        "radius": radius,
        "radius_vars": radius_vars,
        "unmapped_colour_vars": sorted(
            name
            for name, value in light_vars.items()
            if parse_color(resolve(value, light_vars))
            and "--" + name not in role_source.values()
        )[:40],
        "raw_light_vars": {
            name: resolve(value, light_vars)
            for name, value in light_vars.items()
            if parse_color(resolve(value, light_vars))
        },
        "raw_dark_vars": {
            name: resolve(value, dark_vars)
            for name, value in modes["dark"].items()
            if parse_color(resolve(split_light_dark(value, True), dark_vars))
        },
    }


def main() -> int:
    records = json.loads(Path("data/scan.json").read_text(encoding="utf-8"))
    extracted = [extract_repo(record) for record in records if record["files"]]
    Path("data/extracted.json").write_text(json.dumps(extracted, indent=1), encoding="utf-8")

    usable = 0
    for item in extracted:
        light = item["light"]
        if light.get("bg") and light.get("ink"):
            usable += 1
        roles = " ".join(f"{role}={light[role][1:]}" for role in ("bg", "surface", "ink", "muted", "line", "accent") if role in light)
        fonts = "/".join(first_family(item["fonts"][key]) or "-" for key in ("display", "body", "mono"))
        dark_flag = "D" if item["dark"].get("bg") else "-"
        doc_flag = "M" if item["has_design_doc"] else "-"
        print(
            f"{item['repo'][:22]:<22} {item['visibility'][:3]} {dark_flag}{doc_flag} v{item['var_count']:<3} "
            f"{roles} | {fonts} | r={item['radius']}"
        )
    print(f"ALL_DONE extracted={len(extracted)} usable={usable}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
