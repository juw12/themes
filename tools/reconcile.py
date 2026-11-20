"""Merge the repo CSS extraction with the rendered live probe into one record per project.

Priority per value (first that exists wins):
  bg      rendered page background
  ink     declared text variable on the live page > repo CSS variable > rendered body colour
  accent  declared variable (live, then repo CSS) > strongest painted button / link colour
  other   declared variable (live, then repo CSS)
  fonts   rendered heading / body font stacks; mono from the page, else the repo CSS variable
  radius  declared radius variable > rendered panel radius > rendered button radius
Hand corrections live in curation.json and are applied by build.py, never here.
Writes data/merged.json and prints a review table.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from colors import contrast, hue_sat, over, parse_color, to_hex  # noqa: E402
from extract import GENERIC_FAMILIES, MONO_HINT, ROLE_NAMES, first_family, normalise_name  # noqa: E402

ROLE_ORDER = ("bg", "surface", "ink", "muted", "line", "accent", "accent2", "ok", "warn", "bad")
RADIUS_NAMES = ("radius", "r", "radius-md", "radius-card", "radius-m", "r-md", "rad", "radius-lg", "r-lg")


def roles_from_vars(root_vars: dict) -> tuple[dict, dict]:
    colours = {}
    for name, value in root_vars.items():
        parsed = parse_color(value or "")
        if parsed:
            colours[name.lstrip("-")] = parsed
    roles, sources = {}, {}
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
            sources[role] = "--" + best[1]
    return roles, sources


def saturated(rgb) -> bool:
    _hue, sat, light = hue_sat(rgb)
    return sat > 0.3 and 0.15 < light < 0.8


def close(first: str, second: str, tolerance: int = 10) -> bool:
    a, b = parse_color(first), parse_color(second)
    if not a or not b:
        return False
    return all(abs(a[i] - b[i]) <= tolerance for i in range(3))


def clean_stack(stack: str) -> str:
    families = [family.strip().strip("\"'") for family in (stack or "").split(",") if family.strip()]
    quoted = []
    for family in families:
        needs_quotes = " " in family and family.lower() not in GENERIC_FAMILIES
        quoted.append(f'"{family}"' if needs_quotes else family)
    return ", ".join(quoted)


def px_or_empty(value: str) -> str:
    return value if re.fullmatch(r"\d+(\.\d+)?(px|rem)", value or "") else ""


def from_live(probe: dict, css: dict | None) -> dict | None:
    if not probe or "error" in probe or "background" not in probe:
        return None
    background = parse_color(probe["background"])
    if not background:
        return None
    background = (*over(background, (255, 255, 255)), 1.0)
    root_vars = probe.get("rootVars", {})
    declared, sources = roles_from_vars(root_vars)
    roles = {"bg": to_hex(background)}
    origin = {"bg": "rendered page background"}
    flags = []

    if "bg" in declared and not close(to_hex(over(declared["bg"], background)), roles["bg"], 12):
        flags.append(f"bg: rendered {roles['bg']} but {sources['bg']} = {to_hex(declared['bg'])}")

    for role, colour in declared.items():
        if role == "bg":
            continue
        roles[role] = to_hex(over(colour, background))
        origin[role] = f"{sources[role]} on the live page"

    if "ink" not in roles:
        for key in ("bodyColorDirect", "color"):
            parsed = parse_color(probe.get(key, ""))
            if parsed:
                roles["ink"] = to_hex(over(parsed, background))
                origin["ink"] = "rendered body text"
                break

    painted = []
    accent_ink = ""
    for button in probe.get("filled", []):
        colour = parse_color(button["background"])
        if colour and colour[3] > 0.6 and saturated(colour):
            painted.append((to_hex(over(colour, background)), button.get("color", "")))
    for value, _count in sorted(probe.get("linkColours", {}).items(), key=lambda item: -item[1]):
        colour = parse_color(value)
        if colour and saturated(colour):
            painted.append((to_hex(over(colour, background)), ""))

    if "accent" not in roles and css and css["light"].get("accent") and "accent" not in css["inferred"]:
        roles["accent"] = css["light"]["accent"]
        origin["accent"] = css["role_source"].get("accent", "repo CSS") + " in the repo CSS"
    if "accent" not in roles and painted:
        roles["accent"] = painted[0][0]
        origin["accent"] = "strongest painted button / link"
        flags.append("accent: no declared variable, taken from what the page paints")
    if "accent" in roles:
        for colour_hex, text in painted:
            text_colour = parse_color(text)
            if text_colour and close(colour_hex, roles["accent"], 8):
                accent_ink = to_hex(text_colour)
                break

    if "surface" not in roles:
        for surface in probe.get("surfaces", []):
            colour = parse_color(surface.split("|")[0])
            if colour and not close(to_hex(over(colour, background)), roles["bg"], 3):
                roles["surface"] = to_hex(over(colour, background))
                origin["surface"] = "largest painted panel"
                break

    radius = ""
    for name in RADIUS_NAMES:
        value = (root_vars.get("--" + name) or "").strip()
        if px_or_empty(value):
            radius = value
            break
    if not radius and css:
        radius = px_or_empty(css["radius"])
    if not radius:
        for surface in probe.get("surfaces", []):
            candidate = surface.split("|")[3]
            if px_or_empty(candidate) and candidate != "0px" and float(candidate[:-2]) < 60:
                radius = candidate
                break
    if not radius:
        for button in probe.get("filled", []):
            candidate = button.get("radius", "")
            if px_or_empty(candidate) and float(candidate[:-2]) < 60:
                radius = candidate
                break

    mono = clean_stack(probe.get("monoFont", ""))
    if not MONO_HINT.search(mono):
        mono = clean_stack(css["fonts"]["mono"]) if css and MONO_HINT.search(css["fonts"]["mono"] or "") else ""

    extras = {}
    used = {value for value in roles.values()}
    for name, value in root_vars.items():
        parsed = parse_color(value or "")
        if not parsed or parsed[3] < 1:
            continue
        colour_hex = to_hex(parsed)
        if colour_hex in used or not saturated(parsed):
            continue
        if re.search(r"soft|pale|bg|hover|dark|deep|ink|focus|shadow|glow|tint|-\d$", name):
            continue
        extras[name.lstrip("-")] = colour_hex
        used.add(colour_hex)
        if len(extras) >= 5:
            break

    return {
        "roles": roles,
        "origin": origin,
        "flags": flags,
        "accent_ink": accent_ink,
        "extras": extras,
        "fonts": {
            "display": clean_stack(probe.get("headingFont", "")),
            "body": clean_stack(probe.get("bodyFontDirect") or probe.get("bodyFont", "")),
            "mono": mono,
            "loaded": sorted(set(probe.get("loadedFonts", []))),
        },
        "type": {
            "body_size": probe.get("bodySize", ""),
            "heading_weight": probe.get("headingWeight", ""),
            "heading_style": probe.get("headingStyle", ""),
            "heading_transform": probe.get("headingTransform", ""),
        },
        "radius": radius,
        "title": probe.get("title", ""),
    }


def main() -> int:
    extracted = {item["repo"]: item for item in json.loads(Path("data/extracted.json").read_text(encoding="utf-8"))}
    scan = {item["repo"]: item for item in json.loads(Path("data/scan.json").read_text(encoding="utf-8"))}
    live_path = Path("data/live.json")
    live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else {}

    merged = {}
    for repo, record in scan.items():
        css = extracted.get(repo)
        probe = live.get(repo, {})
        css_usable = bool(css and css["light"].get("bg") and css["light"].get("ink"))
        landing_only = "/p/" in record["homepage"]
        use_live = not (landing_only and css_usable)
        light_live = from_live(probe.get("light"), css) if use_live else None
        dark_live = from_live(probe.get("dark"), css) if use_live else None

        entry = {
            "repo": repo,
            "visibility": record["visibility"],
            "archived": record["archived"],
            "homepage": record["homepage"],
            "description": record["description"],
            "pushed": record["pushed"],
            "source": "none",
            "landing_only": landing_only and not css_usable,
            "light": {},
            "dark": {},
            "origin": {},
            "fonts": {},
            "type": {},
            "extras": {},
            "accent_ink": "",
            "radius": "",
            "flags": [],
            "has_design_doc": bool(css and css["has_design_doc"]),
            "variants": css["variants"] if css else [],
            "files": css["files"] if css else [],
        }
        if light_live:
            entry["source"] = "live page"
            entry["light"] = light_live["roles"]
            entry["origin"] = light_live["origin"]
            entry["fonts"] = light_live["fonts"]
            entry["type"] = light_live["type"]
            entry["extras"] = light_live["extras"]
            entry["accent_ink"] = light_live["accent_ink"]
            entry["radius"] = light_live["radius"]
            entry["title"] = light_live["title"]
            entry["flags"] = light_live["flags"]
            if dark_live and not close(dark_live["roles"]["bg"], light_live["roles"]["bg"], 6):
                entry["dark"] = dark_live["roles"]
            if css:
                for role, value in css["light"].items():
                    if role not in entry["light"] and role not in css["inferred"]:
                        entry["light"][role] = value
                        entry["origin"][role] = css["role_source"].get(role, "repo CSS") + " in the repo CSS"
        elif css_usable:
            entry["source"] = "repo CSS"
            entry["light"] = dict(css["light"])
            entry["origin"] = {role: css["role_source"].get(role, "repo CSS") + " in the repo CSS" for role in css["light"]}
            if css["dark"].get("bg") and css["dark"]["bg"] != css["light"]["bg"]:
                entry["dark"] = css["dark"]
            entry["fonts"] = {
                "display": clean_stack(css["fonts"]["display"]),
                "body": clean_stack(css["fonts"]["body"]),
                "mono": clean_stack(css["fonts"]["mono"]),
                "loaded": css["fonts"]["google"] + css["fonts"]["faces"],
            }
            entry["radius"] = px_or_empty(css["radius"])
            entry["flags"].append("not rendered (no public live app page)")
            entry["flags"] += [f"{role}: inferred from the most used colour" for role in css["inferred"]]

        if entry["light"].get("bg") and entry["light"].get("ink"):
            ratio = contrast(parse_color(entry["light"]["bg"]), parse_color(entry["light"]["ink"]))
            if ratio < 4.5:
                entry["flags"].append(f"ink on bg contrast {ratio:.2f}")
        merged[repo] = entry

    Path("data/merged.json").write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")

    for repo, entry in merged.items():
        if entry["source"] == "none":
            continue
        light = entry["light"]
        roles = " ".join(f"{role}={light[role][1:]}" for role in ROLE_ORDER[:6] if role in light)
        fonts = "/".join(first_family(entry["fonts"].get(key, "")) or "-" for key in ("display", "body", "mono"))
        dark = ("D:" + entry["dark"]["bg"][1:]) if entry["dark"].get("bg") else "-"
        tag = "L" if entry["source"] == "live page" else "C"
        tag += "p" if entry["landing_only"] else " "
        extras = ",".join(f"{name}={value[1:]}" for name, value in entry["extras"].items())
        print(f"{repo[:20]:<20} {entry['visibility'][:3]} {tag} {roles} {dark} | {fonts} | r={entry['radius']} | {extras}")
        for flag in entry["flags"]:
            print(f"      ! {flag}")
    none = [repo for repo, entry in merged.items() if entry["source"] == "none"]
    print(f"themes={len(merged) - len(none)} no theme ({len(none)}):", ", ".join(none))
    return 0


if __name__ == "__main__":
    sys.exit(main())
