"""Build the theme library from src/merged.json (the scan) and src/curation.json (names + fixes).

    python tools/build.py            writes themes/<id>.json, themes/<id>.css and themes.json

Rules this file enforces:
- every colour comes from the project's own CSS or its rendered page (src/evidence.json),
  or is listed under "derived" with how it was worked out;
- a hand fix needs a written reason in src/curation.json;
- contrast numbers are computed here, never typed in.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import colors as C  # noqa: E402

SCHEMA = 1
OWNER = "juw12"
CORE_ROLES = ["bg", "surface", "ink", "muted", "line", "accent", "accent_ink"]
OPTIONAL_ROLES = ["surface_ink", "accent2", "ok", "warn", "bad"]
ROLE_ORDER = CORE_ROLES + OPTIONAL_ROLES
FALLBACK_MONO = "ui-monospace, Consolas, monospace"
# Families that Google Fonts serves; anything else in a stack is a system font.
WEB_FAMILIES = {
    "Instrument Serif": "Instrument+Serif:ital@0;1",
    "Instrument Sans": "Instrument+Sans:wght@400;500;600;700",
    "Geist": "Geist:wght@400;500;600;700",
    "Geist Mono": "Geist+Mono:wght@400;500",
    "Inter": "Inter:wght@400;500;600;700",
    "Bricolage Grotesque": "Bricolage+Grotesque:wght@400;600;800",
    "IBM Plex Sans": "IBM+Plex+Sans:wght@400;500;600",
    "IBM Plex Sans Condensed": "IBM+Plex+Sans+Condensed:wght@500;600;700",
    "IBM Plex Mono": "IBM+Plex+Mono:wght@400;500",
    "Roboto Slab": "Roboto+Slab:wght@400;600;700",
    "Source Serif 4": "Source+Serif+4:wght@400;600;700",
    "Source Sans 3": "Source+Sans+3:wght@400;600;700",
    "Libre Caslon Display": "Libre+Caslon+Display",
    "JetBrains Mono": "JetBrains+Mono:wght@400;500;700",
    "Fraunces": "Fraunces:wght@400;600;700",
    "Figtree": "Figtree:wght@400;500;600;700",
    "Manrope": "Manrope:wght@400;500;600;700",
    "Barlow Semi Condensed": "Barlow+Semi+Condensed:wght@500;600;700",
    "DM Serif Display": "DM+Serif+Display",
    "Jost": "Jost:wght@400;500;600",
    "Cormorant Garamond": "Cormorant+Garamond:wght@400;500;600;700",
}


def rgb(value):
    return C.parse_color(value)


def contrast(a, b):
    return round(C.contrast(rgb(a), rgb(b)), 2)


def mix(a, b, share_of_b):
    """Blend two hex colours; share_of_b = 0 gives a, 1 gives b."""
    ra, rb = rgb(a), rgb(b)
    parts = [round(ra[i] + (rb[i] - ra[i]) * share_of_b) for i in range(3)]
    return "#%02x%02x%02x" % tuple(parts)


def families(stack):
    names = []
    for part in (stack or "").split(","):
        name = part.strip().strip("\"'")
        if name:
            names.append(name)
    return names


def first_family(stack):
    names = families(stack)
    return names[0] if names else ""


def web_fonts(fonts):
    # Only the first family of a stack is ever painted when it loads, so only that one is fetched.
    found = []
    for stack in (fonts["display"], fonts["body"], fonts["mono"]):
        name = first_family(stack)
        if name in WEB_FAMILIES and name not in found:
            found.append(name)
    return found


def google_fonts_url(names):
    if not names:
        return ""
    query = "&".join("family=" + WEB_FAMILIES[name] for name in names)
    return "https://fonts.googleapis.com/css2?" + query + "&display=swap"


def derive_muted(ink, bg):
    """Soften the ink toward the page until just before it would drop under 4.5:1."""
    best = ink
    for step in range(1, 12):
        candidate = mix(ink, bg, step * 0.05)
        if contrast(candidate, bg) < 4.6:
            break
        best = candidate
    return best


def best_text_on(fill, candidates):
    return max(candidates, key=lambda colour: contrast(colour, fill))


def complete(colours, origin, declared_accent_ink, scheme_label):
    """Fill the roles a project did not declare. Returns (colours, origin, derived list)."""
    derived = []
    out = dict(colours)
    where = dict(origin)
    if "surface" not in out:
        out["surface"] = out["bg"]
        where["surface"] = "derived: same as bg (no panel colour declared)"
        derived.append("surface")
    if "muted" not in out:
        out["muted"] = derive_muted(out["ink"], out["bg"])
        where["muted"] = "derived: ink softened toward bg, kept at 4.5:1 or better"
        derived.append("muted")
    if "line" not in out:
        out["line"] = mix(out["bg"], out["ink"], 0.16)
        where["line"] = "derived: 16% ink over bg"
        derived.append("line")
    if "accent_ink" not in out:
        if declared_accent_ink:
            out["accent_ink"] = declared_accent_ink
            where["accent_ink"] = "text colour painted on the accent fill"
        else:
            out["accent_ink"] = best_text_on(out["accent"], ["#ffffff", out["ink"], out["bg"]])
            where["accent_ink"] = "derived: best contrast on the accent out of white, ink and bg"
            derived.append("accent_ink")
    ordered = {role: out[role] for role in ROLE_ORDER if role in out}
    where = {role: where.get(role, scheme_label) for role in ordered}
    return ordered, where, derived


def measure(colours):
    numbers = {
        "ink_on_bg": contrast(colours["ink"], colours["bg"]),
        "muted_on_bg": contrast(colours["muted"], colours["bg"]),
        "accent_on_bg": contrast(colours["accent"], colours["bg"]),
        "accent_ink_on_accent": contrast(colours["accent_ink"], colours["accent"]),
    }
    surface_text = colours.get("surface_ink", colours["ink"])
    numbers["ink_on_surface"] = contrast(surface_text, colours["surface"])
    return numbers


def warnings_for(numbers, label):
    notes = []
    checks = [
        ("ink_on_bg", "ink on bg"),
        ("muted_on_bg", "muted on bg"),
        ("accent_ink_on_accent", "accent_ink on accent"),
        ("ink_on_surface", "ink on surface"),
    ]
    for key, words in checks:
        if numbers[key] < 4.5:
            notes.append(f"{label}: {words} is {numbers[key]}:1, under the 4.5:1 needed for body text")
    if numbers["accent_on_bg"] < 3:
        notes.append(
            f"{label}: accent on bg is {numbers['accent_on_bg']}:1, under 3:1; "
            "pair it with a border or use it on a darker panel"
        )
    elif numbers["accent_on_bg"] < 4.5:
        notes.append(
            f"{label}: accent on bg is {numbers['accent_on_bg']}:1; fine for fills and large text, not for small text"
        )
    return notes


def describe(theme):
    colours = theme["colors"]
    hue = C.hue_name(rgb(colours["accent"]))
    display = first_family(theme["fonts"]["display"])
    body = first_family(theme["fonts"]["body"])
    type_words = display if display == body else f"{display} over {body}"
    dark_words = ", with a dark set" if theme["dark"] else ""
    return f"{theme['scheme'].capitalize()} ground {colours['bg']}, {hue} accent {colours['accent']}, {type_words}{dark_words}."


def build_theme(entry, merged, evidence, checked, public_repos):
    over = entry.get("override", {})
    reasons = over.get("reasons", {})
    manual = entry.get("manual")
    if manual:
        record = {
            "source": manual["source"],
            "light": manual["light"],
            "dark": None,
            "origin": {role: "declared in " + manual["file"] for role in manual["light"]},
            "fonts": manual["fonts"],
            "extras": manual["extras"],
            "accent_ink": manual.get("accent_ink", ""),
            "radius": manual["radius"],
            "type": {},
            "files": [manual["file"]],
        }
    else:
        record = merged[entry["base"]]

    light = dict(record["light"])
    origin = dict(record.get("origin") or {})
    for role, value in (over.get("light") or {}).items():
        light[role] = value
        origin[role] = "curated: " + reasons[role]
    for needed in ("bg", "ink", "accent"):
        if needed not in light:
            raise SystemExit(f"{entry['id']}: no {needed} colour; add it to src/curation.json with a reason")
    # The painted button text only belongs to the accent the scan found, not to a curated one.
    painted_ink = "" if "accent" in (over.get("light") or {}) else (record.get("accent_ink") or "")
    light, light_origin, derived = complete(light, origin, painted_ink, "from the " + record["source"])

    dark = None
    dark_origin = {}
    dark_derived = []
    source_dark = dict(record.get("dark") or {})
    for role, value in (over.get("dark") or {}).items():
        source_dark[role] = value
    if all(role in source_dark for role in ("bg", "ink", "accent")):
        same_accent = source_dark["accent"] == light["accent"]
        declared = light["accent_ink"] if same_accent and "accent_ink" not in derived else ""
        labels = {role: "dark scheme of the " + record["source"] for role in source_dark}
        for role in over.get("dark") or {}:
            labels[role] = "curated: " + reasons.get(role, "see light")
        dark, dark_origin, dark_derived = complete(source_dark, labels, declared, "dark scheme")

    fonts_in = dict(record.get("fonts") or {})
    for key, value in (over.get("fonts") or {}).items():
        fonts_in[key] = value
    body = fonts_in.get("body") or fonts_in.get("display") or "system-ui, sans-serif"
    fonts = {
        "display": fonts_in.get("display") or body,
        "body": body,
        "mono": fonts_in.get("mono") or FALLBACK_MONO,
    }
    if not fonts_in.get("mono"):
        derived.append("fonts.mono")
    if not fonts_in.get("display"):
        derived.append("fonts.display")
    fonts["web"] = web_fonts(fonts)
    fonts["web_url"] = google_fonts_url(fonts["web"])

    extras = dict(record.get("extras") or {})
    extras.update(over.get("extras") or {})

    known = set()
    for repo in entry["projects"]:
        known |= set(evidence.get(repo, []))
    for scheme_name, colours, skip in (("light", light, derived), ("dark", dark or {}, dark_derived)):
        for role, value in colours.items():
            if role in skip:
                continue
            if value not in known:
                raise SystemExit(f"{entry['id']}: {scheme_name} {role} {value} is not in the project's CSS or page")
    for name, value in extras.items():
        if value not in known:
            raise SystemExit(f"{entry['id']}: extra {name} {value} is not in the project's CSS or page")

    is_dark = C.luminance(rgb(light["bg"])) < 0.2
    type_info = record.get("type") or {}
    theme = {
        "schema": SCHEMA,
        "id": entry["id"],
        "name": entry["name"],
        "summary": "",
        "note": entry["note"],
        "scheme": "dark" if is_dark else "light",
        "hue": C.hue_name(rgb(light["accent"])),
        "projects": [
            {
                "repo": repo,
                "url": f"https://github.com/{OWNER}/{repo}",
                "live": (merged.get(repo) or {}).get("homepage") or "",
            }
            for repo in entry["projects"]
            if repo in public_repos
        ],
        "source": record["source"],
        "checked": checked,
        "colors": light,
        "dark": dark,
        "extras": extras,
        "fonts": fonts,
        "radius": over.get("radius") or record.get("radius") or "8px",
        "heading_weight": str(type_info.get("heading_weight") or ""),
        "contrast": {"light": measure(light)},
        "origin": {"light": light_origin},
        "derived": derived + ["dark." + role for role in dark_derived],
        "curated": {key: reason for key, reason in reasons.items()},
        "warnings": [],
    }
    theme["warnings"] = warnings_for(theme["contrast"]["light"], "light" if not is_dark else "dark ground")
    if dark:
        theme["contrast"]["dark"] = measure(dark)
        theme["origin"]["dark"] = dark_origin
        theme["warnings"] += warnings_for(theme["contrast"]["dark"], "dark set")
    theme["summary"] = describe(theme)
    return theme


def css_block(colours, fonts, radius, extras, indent="  "):
    lines = []
    for role in ROLE_ORDER:
        if role in colours:
            lines.append(f"{indent}--{role.replace('_', '-')}: {colours[role]};")
    if extras is not None:
        for name, value in extras.items():
            lines.append(f"{indent}--x-{name}: {value};")
    if fonts is not None:
        lines.append(f"{indent}--font-display: {fonts['display']};")
        lines.append(f"{indent}--font-body: {fonts['body']};")
        lines.append(f"{indent}--font-mono: {fonts['mono']};")
        lines.append(f"{indent}--radius: {radius};")
    return "\n".join(lines)


def theme_css(theme):
    names = ", ".join(project["repo"] for project in theme["projects"])
    head = [
        f"/* {theme['name']} ({theme['id']})",
        f"   {theme['summary']}",
        f"   From: {names}. Read from the {theme['source']}, checked {theme['checked']}.",
        f"   https://{OWNER}.github.io/themes/#{theme['id']}",
    ]
    if theme["fonts"]["web_url"]:
        head.append(f"   Web fonts: {theme['fonts']['web_url']}")
    head.append("*/")
    scheme = "dark" if theme["scheme"] == "dark" else ("light dark" if theme["dark"] else "light")
    parts = ["\n".join(head), ":root {", f"  color-scheme: {scheme};"]
    parts.append(css_block(theme["colors"], theme["fonts"], theme["radius"], theme["extras"]))
    parts.append("}")
    if theme["dark"]:
        parts.append("@media (prefers-color-scheme: dark) {")
        parts.append("  :root {")
        parts.append(css_block(theme["dark"], None, None, None, indent="    "))
        parts.append("  }")
        parts.append("}")
    return "\n".join(parts) + "\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def build_all(curation, merged, evidence, public_repos):
    themes = [
        build_theme(entry, merged, evidence, curation["checked"], public_repos)
        for entry in curation["themes"]
    ]
    ids = [theme["id"] for theme in themes]
    names = [theme["name"] for theme in themes]
    if len(set(ids)) != len(ids) or len(set(names)) != len(names):
        raise SystemExit("theme ids and names must be unique")
    return themes


def main():
    curation = load_json(os.path.join(ROOT, "src", "curation.json"))
    merged = load_json(os.path.join(ROOT, "src", "merged.json"))
    evidence = load_json(os.path.join(ROOT, "src", "evidence.json"))
    themes = build_all(curation, merged, evidence, set(merged))
    out_dir = os.path.join(ROOT, "themes")
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, name))
    for theme in themes:
        write(os.path.join(out_dir, theme["id"] + ".json"), json.dumps(theme, indent=2, ensure_ascii=False) + "\n")
        write(os.path.join(out_dir, theme["id"] + ".css"), theme_css(theme))
    index = {
        "schema": SCHEMA,
        "checked": curation["checked"],
        "count": len(themes),
        "themes": [
            {
                "id": theme["id"],
                "name": theme["name"],
                "summary": theme["summary"],
                "scheme": theme["scheme"],
                "has_dark": bool(theme["dark"]),
                "hue": theme["hue"],
                "projects": [project["repo"] for project in theme["projects"]],
                "bg": theme["colors"]["bg"],
                "ink": theme["colors"]["ink"],
                "accent": theme["colors"]["accent"],
                "display": first_family(theme["fonts"]["display"]),
                "body": first_family(theme["fonts"]["body"]),
                "json": f"themes/{theme['id']}.json",
                "css": f"themes/{theme['id']}.css",
            }
            for theme in themes
        ],
    }
    write(os.path.join(ROOT, "themes.json"), json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    print(f"built {len(themes)} themes")
    return themes


if __name__ == "__main__":
    main()
