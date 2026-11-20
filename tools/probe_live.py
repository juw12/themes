"""Read the rendered look of each project's live page (the ground truth for the extractor).

For every repo with a homepage, opens the page in headless Chromium in light and dark colour scheme and
records the computed page background, text colour, fonts, the primary button colour and the :root
custom properties. Writes data/live.json. Read-only.

Usage: probe_live.py [--only repo1,repo2]
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROBE_JS = r"""
() => {
  const visible = (el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return box.width > 4 && box.height > 4 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const opaque = (colour) => colour && colour !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(colour);
  const pageBackground = () => {
    for (const el of [document.body, document.documentElement]) {
      const colour = getComputedStyle(el).backgroundColor;
      if (opaque(colour)) return colour;
    }
    return 'rgb(255, 255, 255)';
  };
  const firstVisible = (selector) => [...document.querySelectorAll(selector)].find(visible);

  const heading = firstVisible('h1') || firstVisible('h2') || firstVisible('h3');
  const code = firstVisible('code, pre, kbd, .mono, .num');
  const paragraph = firstVisible('main p, p, li, td, label') || document.body;

  const filled = [];
  for (const el of document.querySelectorAll('button, a, [role=button], input[type=submit], .btn')) {
    if (!visible(el)) continue;
    const style = getComputedStyle(el);
    if (opaque(style.backgroundColor)) {
      const box = el.getBoundingClientRect();
      filled.push({ background: style.backgroundColor, color: style.color, area: Math.round(box.width * box.height), radius: style.borderTopLeftRadius });
    }
  }
  const linkColours = {};
  for (const el of document.querySelectorAll('a')) {
    if (!visible(el)) continue;
    const colour = getComputedStyle(el).color;
    linkColours[colour] = (linkColours[colour] || 0) + 1;
  }

  const surfaces = {};
  for (const el of document.querySelectorAll('section, article, aside, .card, .panel, [class*=card], [class*=panel], dialog, nav, header')) {
    if (!visible(el)) continue;
    const style = getComputedStyle(el);
    if (!opaque(style.backgroundColor)) continue;
    const key = style.backgroundColor + '|' + style.borderTopColor + '|' + style.borderTopWidth + '|' + style.borderTopLeftRadius;
    const box = el.getBoundingClientRect();
    surfaces[key] = (surfaces[key] || 0) + Math.round(box.width * box.height);
  }

  const rootVars = {};
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (error) { continue; }
    for (const rule of rules) {
      if (rule.selectorText && /(^|,)\s*(:root|html)\s*(,|$)/.test(rule.selectorText)) {
        for (const name of rule.style) {
          if (name.startsWith('--')) rootVars[name] = null;
        }
      }
    }
  }
  const rootStyle = getComputedStyle(document.documentElement);
  for (const name of Object.keys(rootVars)) rootVars[name] = rootStyle.getPropertyValue(name).trim();

  const bodyStyle = getComputedStyle(document.body);
  const headingStyle = heading ? getComputedStyle(heading) : null;
  return {
    title: document.title,
    background: pageBackground(),
    color: getComputedStyle(paragraph).color,
    bodyFont: getComputedStyle(paragraph).fontFamily,
    bodyColorDirect: bodyStyle.color,
    bodyFontDirect: bodyStyle.fontFamily,
    bodySize: bodyStyle.fontSize,
    bodyLineHeight: bodyStyle.lineHeight,
    headingSize: headingStyle ? headingStyle.fontSize : '',
    headingTracking: headingStyle ? headingStyle.letterSpacing : '',
    headingStyle: headingStyle ? headingStyle.fontStyle : '',
    headingTransform: headingStyle ? headingStyle.textTransform : '',
    headingFont: heading ? getComputedStyle(heading).fontFamily : '',
    headingWeight: heading ? getComputedStyle(heading).fontWeight : '',
    headingColor: heading ? getComputedStyle(heading).color : '',
    monoFont: code ? getComputedStyle(code).fontFamily : '',
    filled: filled.sort((a, b) => b.area - a.area).slice(0, 8),
    linkColours,
    surfaces: Object.entries(surfaces).sort((a, b) => b[1] - a[1]).slice(0, 5).map((entry) => entry[0]),
    rootVars,
    loadedFonts: [...document.fonts].filter((face) => face.status === 'loaded').map((face) => face.family.replace(/["']/g, '')),
  };
}
"""


def main() -> None:
    only = set()
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    scan = json.loads(Path("data/scan.json").read_text(encoding="utf-8"))
    targets = [
        record
        for record in scan
        if record["homepage"].startswith("https://")
        and ("github.io" in record["homepage"] or "pages.dev" in record["homepage"])
        and (not only or record["repo"] in only)
    ]
    out_path = Path("data/live.json")
    results = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() and only else {}

    proxy = os.environ.get("PROBE_PROXY", "")
    with sync_playwright() as playwright:
        launch_args = {"headless": True}
        if proxy:
            launch_args["proxy"] = {"server": proxy}
        browser = playwright.chromium.launch(**launch_args)
        for index, record in enumerate(targets, start=1):
            entry = {"url": record["homepage"]}
            for scheme in ("light", "dark"):
                context = browser.new_context(
                    color_scheme=scheme, viewport={"width": 1280, "height": 900}, service_workers="block"
                )
                page = context.new_page()
                try:
                    try:
                        page.goto(record["homepage"], wait_until="networkidle", timeout=25000)
                    except Exception:
                        page.goto(record["homepage"], wait_until="load", timeout=25000)
                    page.wait_for_timeout(600)
                    entry[scheme] = page.evaluate(PROBE_JS)
                except Exception as error:  # noqa: BLE001 - one bad page must not stop the scan
                    entry[scheme] = {"error": str(error).splitlines()[0][:160]}
                page.close()
            results[record["repo"]] = entry
            light = entry.get("light", {})
            print(
                f"{index:>2}/{len(targets)} {record['repo']:<24} "
                f"{light.get('background', light.get('error', ''))} vars={len(light.get('rootVars', {}))}",
                flush=True,
            )
            out_path.write_text(json.dumps(results, indent=1), encoding="utf-8")

    print(f"ALL_DONE probed={len(results)}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
