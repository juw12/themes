"""Write index.html (the specimen book), components.html (the React Bits shelf), README.md and TEMPLATES.md.

    python tools/build.py && python tools/site.py
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build as B  # noqa: E402

REPO_URL = "https://github.com/juw12/themes"
RAW_URL = "https://raw.githubusercontent.com/juw12/themes/main"
SITE_URL = "https://juw12.github.io/themes/"
HOUSE_THEME = "cairn-paper"
SWATCH_ROLES = ["bg", "surface", "ink", "muted", "line", "accent"]
HUES = ["red", "orange", "yellow", "green", "teal", "blue", "violet", "pink"]
STATS_FILE = os.path.join(ROOT, "src", "scan_stats.json")
SHELF_FILE = os.path.join(ROOT, "reactbits.json")
SHELF_PAGE = "components.html"


def esc(value):
    return html.escape(str(value), quote=True)


def style_vars(colours, fonts=None, radius=None):
    parts = [f"--{role.replace('_', '-')}:{value}" for role, value in colours.items()]
    if "surface_ink" not in colours:
        parts.append(f"--surface-ink:{colours['ink']}")
    if fonts:
        parts.append(f"--font-display:{fonts['display']}")
        parts.append(f"--font-body:{fonts['body']}")
        parts.append(f"--font-mono:{fonts['mono']}")
        parts.append(f"--radius:{radius}")
    return ";".join(parts)


def short(text, limit=120):
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",.;:")
    return cut + "..."


def font_line(fonts):
    names = []
    for key in ("display", "body", "mono"):
        name = B.first_family(fonts[key])
        if name not in names:
            names.append(name)
    return " / ".join(names)


def token_rows(theme, scheme):
    colours = theme["colors"] if scheme == "light" else theme["dark"]
    origin = theme["origin"][scheme]
    rows = []
    for role, value in colours.items():
        rows.append(
            "<tr>"
            f'<th scope="row"><span class="dot" style="background:{value}"></span>{esc(role)}</th>'
            f"<td><code>{value}</code></td>"
            f"<td>{esc(origin.get(role, ''))}</td>"
            "</tr>"
        )
    return "".join(rows)


def contrast_rows(numbers):
    labels = [
        ("ink_on_bg", "ink on bg"),
        ("ink_on_surface", "ink on surface"),
        ("muted_on_bg", "muted on bg"),
        ("accent_on_bg", "accent on bg"),
        ("accent_ink_on_accent", "accent-ink on accent"),
    ]
    cells = []
    for key, words in labels:
        value = numbers[key]
        grade = "pass" if value >= 4.5 else ("large" if value >= 3 else "low")
        cells.append(f'<li class="c-{grade}"><b>{value}</b> {words}</li>')
    return "".join(cells)


def card(theme, number):
    colours = theme["colors"]
    fonts = theme["fonts"]
    projects = ", ".join(
        f'<a href="{esc(p["live"] or p["url"])}">{esc(p["repo"])}</a>' for p in theme["projects"]
    )
    swatches = "".join(
        f'<li><button type="button" class="chip" data-copy="{colours[role]}" data-role="{role}" '
        f'aria-label="Copy {role} {colours[role]}">'
        f'<span class="chip-ink" style="background:{colours[role]}" data-swatch="{role}"></span>'
        f"<span class=\"chip-role\">{role}</span><code data-hex=\"{role}\">{colours[role]}</code></button></li>"
        for role in SWATCH_ROLES
    )
    toggle = ""
    if theme["dark"]:
        toggle = (
            '<div class="mode" role="group" aria-label="Scheme">'
            '<button type="button" class="mode-btn" data-mode="light" aria-pressed="true">Light</button>'
            '<button type="button" class="mode-btn" data-mode="dark" aria-pressed="false">Dark</button>'
            "</div>"
        )
    extras = ""
    if theme["extras"]:
        items = "".join(
            f'<li><span class="dot" style="background:{value}"></span>{esc(name)} <code>{value}</code></li>'
            for name, value in theme["extras"].items()
        )
        extras = f'<h4>Extras the project also uses</h4><ul class="extras">{items}</ul>'
    warnings = ""
    if theme["warnings"]:
        items = "".join(f"<li>{esc(text)}</li>" for text in theme["warnings"])
        warnings = f'<h4>Watch out</h4><ul class="warn">{items}</ul>'
    curated = ""
    if theme["curated"]:
        items = "".join(f"<li><b>{esc(key)}</b>: {esc(text)}</li>" for key, text in theme["curated"].items())
        curated = f'<h4>Fixed by hand, and why</h4><ul class="warn">{items}</ul>'
    dark_table = ""
    if theme["dark"]:
        dark_table = (
            "<h4>Dark set</h4>"
            f'<table class="tokens"><tbody>{token_rows(theme, "dark")}</tbody></table>'
            f'<ul class="contrast">{contrast_rows(theme["contrast"]["dark"])}</ul>'
        )
    search = " ".join(
        [theme["name"], theme["id"], theme["hue"], theme["scheme"], font_line(fonts)]
        + [p["repo"] for p in theme["projects"]]
    ).lower()
    return f"""
<article class="card" id="{theme['id']}" data-id="{theme['id']}" data-scheme="{theme['scheme']}"
  data-dark="{'yes' if theme['dark'] else 'no'}" data-hue="{theme['hue']}" data-search="{esc(search)}"
  style="{esc(style_vars(colours, fonts, theme['radius']))}">
  <header class="card-top">
    <span class="no">No. {number:02d}</span>
    {toggle}
  </header>
  <h3 class="name">{esc(theme['name'])}</h3>
  <p class="note">{esc(theme['note'])}</p>
  <p class="actions">
    <button type="button" class="btn primary" data-wear="{theme['id']}">Wear it</button>
    <button type="button" class="btn quiet" data-copy-css="{theme['id']}">Copy CSS</button>
    <a class="link" href="themes/{theme['id']}.json">JSON</a>
  </p>
  <div class="panel">
    <ul class="chips">{swatches}</ul>
    <dl class="facts">
      <div><dt>Type</dt><dd>{esc(font_line(fonts))}</dd></div>
      <div><dt>Radius</dt><dd><span class="fig">{esc(theme['radius'])}</span></dd></div>
      <div><dt>From</dt><dd>{projects} <span class="src">({esc(theme['source'])})</span></dd></div>
    </dl>
    <button type="button" class="pull" data-copy="python theme.py pull {theme['id']}"
      aria-label="Copy the pull command for {esc(theme['name'])}"><span class="prompt">$</span> python theme.py pull {theme['id']}</button>
    <details>
      <summary>Every token and where it came from</summary>
      <table class="tokens"><tbody>{token_rows(theme, "light")}</tbody></table>
      <ul class="contrast">{contrast_rows(theme["contrast"]["light"])}</ul>
      {dark_table}{extras}{curated}{warnings}
    </details>
  </div>
</article>"""


def template_section(templates):
    blocks = []
    for group in templates["groups"]:
        rows = "".join(
            "<tr>"
            f'<th scope="row"><a href="{esc(row["url"])}">{esc(row["repo"])}</a>'
            + ('<span class="tag">template</span>' if row["template"] else "")
            + "</th>"
            f'<td class="num" data-label="GitHub stars">{row["stars"]:,}</td>'
            f'<td data-label="Licence">{esc(row["licence"])}</td>'
            f'<td class="num" data-label="Last push">{esc(row["pushed"])}</td>'
            f'<td class="about">{esc(short(row["about"]))}</td>'
            "</tr>"
            for row in group["repos"]
        )
        blocks.append(
            f'<section class="tgroup" id="t-{group["key"]}"><h3>{esc(group["title"])}</h3>'
            f'<p class="lead">{esc(group["lead"])}</p>'
            '<table class="repos"><thead><tr><th scope="col">Repo</th><th scope="col" class="num">GitHub stars</th>'
            '<th scope="col">Licence</th><th scope="col" class="num">Last push</th><th scope="col">In its own words</th>'
            f"</tr></thead><tbody>{rows}</tbody></table></section>"
        )
    return "".join(blocks)


CSS = r"""
*,*::before,*::after{box-sizing:border-box}
[hidden]{display:none !important}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none !important}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--font-body);transition:background .25s,color .25s}
a{color:inherit;text-underline-offset:3px;text-decoration-thickness:1px}
code,.fig,.no,.pull,.eyebrow,.num{font-family:var(--font-mono)}
button{font:inherit;color:inherit;cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.skip{position:absolute;left:-999px;padding:12px 14px}.skip:focus{left:12px;top:12px;background:var(--surface);z-index:9}

/* masthead */
.mast{padding:28px 0 0;border-bottom:1px solid var(--line)}
.mast-row{display:flex;justify-content:space-between;gap:16px;align-items:baseline;flex-wrap:wrap}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0}
.eyebrow a{text-decoration:none;display:inline-block;padding:8px 0}.eyebrow a:hover{text-decoration:underline}
.shelf-link a{color:var(--accent);font-weight:600}
h1{font:400 clamp(40px,8.4vw,104px)/.96 var(--font-display);letter-spacing:-.02em;margin:26px 0 18px;max-width:13ch;text-wrap:balance}
h1 em{font-style:italic;color:var(--accent)}
.standfirst{max-width:62ch;font-size:clamp(17px,1.5vw,19px);margin:0 0 26px;color:var(--ink)}
.tally{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-top:1px solid var(--line);margin:0}
.tally div{padding:14px 16px 16px 0;border-right:1px solid var(--line)}
.tally div+div{padding-left:16px}.tally div:last-child{border-right:0}
.tally dt{font-size:12px;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.tally dd{margin:2px 0 0;font:400 clamp(26px,3.4vw,40px)/1.1 var(--font-display)}
@media (max-width:640px){.tally{grid-template-columns:repeat(2,minmax(0,1fr))}.tally div:nth-child(2){border-right:0}.tally div:nth-child(n+3){border-top:1px solid var(--line)}.tally div:nth-child(3){padding-left:0}}

/* pull strip */
.how{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;padding-top:28px;padding-bottom:28px}
.how h2,.sect h2{font:400 clamp(26px,3vw,36px)/1.1 var(--font-display);margin:0 0 8px;letter-spacing:-.01em}
.how p{margin:0 0 12px;max-width:54ch;color:var(--ink)}
.cmds{display:grid;gap:8px;align-content:start}
.cmd{display:flex;gap:10px;align-items:center;justify-content:space-between;text-align:left;width:100%;background:var(--surface);color:var(--surface-ink,var(--ink));border:1px solid var(--line);border-radius:min(var(--radius),12px);padding:10px 12px;font:13px/1.4 var(--font-mono);min-height:44px}
.cmd span:first-child{overflow-wrap:anywhere;min-width:0}
.cmd .hint{font-family:var(--font-body);font-size:12px;color:var(--muted);flex:none}
@media (max-width:820px){.how{grid-template-columns:minmax(0,1fr)}}

/* filter bar */
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-top:1px solid var(--line);border-bottom:1px solid var(--line);transition:background .25s}
@media (max-width:700px){.bar{position:static}.count{margin-left:0}}
.bar-in{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;padding:10px 0}
.search{flex:1 1 220px;min-width:0;height:44px;padding:0 12px;border:1px solid var(--line);border-radius:min(var(--radius),12px);background:var(--surface);color:var(--surface-ink,var(--ink));font:16px var(--font-body)}
.seg{display:flex;flex-wrap:wrap;gap:6px}
.pill{height:36px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:transparent;font-size:13px;display:inline-flex;align-items:center;gap:6px;white-space:nowrap}
.pill[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.pill .dot{width:10px;height:10px;border-radius:50%;border:1px solid rgba(128,128,128,.35)}
.count{font:12px var(--font-mono);color:var(--muted);margin-left:auto;white-space:nowrap}
.worn{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:8px 0 10px;font-size:14px}
.worn b{font:400 20px/1 var(--font-display)}
.worn button{height:32px;padding:0 12px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--surface-ink,var(--ink));font-size:13px}

/* specimens */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:20px;padding:24px 0 40px}
.card{background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:min(var(--radius),18px);padding:16px 16px 14px;font-family:var(--font-body);min-width:0;display:flex;flex-direction:column;scroll-margin-top:120px}
.card:target{outline:2px solid var(--accent);outline-offset:3px}
.card-top{display:flex;justify-content:space-between;align-items:center;min-height:28px}
.no{font-size:11px;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}
.mode{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}
.mode-btn{border:0;background:transparent;font-size:11px;padding:0 10px;height:26px;color:var(--muted)}
.mode-btn[aria-pressed=true]{background:var(--ink);color:var(--bg)}
.name{font:400 clamp(30px,2.6vw,36px)/1.05 var(--font-display);margin:10px 0 8px;letter-spacing:-.01em;overflow-wrap:anywhere}
.note{margin:0 0 14px;font-size:15px;line-height:1.5;color:var(--ink);min-height:4.5em}
.actions{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:0 0 16px}
.btn{min-height:40px;padding:0 16px;border-radius:var(--radius);border:1px solid transparent;font-size:14px;font-weight:600}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.btn.quiet{background:var(--surface);color:var(--surface-ink,var(--ink));border-color:var(--line)}
.link{color:var(--accent);font-size:14px;font-weight:600;padding:8px 4px}
.panel{background:var(--surface);color:var(--surface-ink,var(--ink));border:1px solid var(--line);border-radius:min(var(--radius),14px);padding:12px;margin-top:auto}
.chips{list-style:none;margin:0 0 10px;padding:0;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}
.chip{display:block;width:100%;padding:0;border:0;background:none;text-align:left}
.chip-ink{display:block;height:44px;border-radius:min(var(--radius),8px);border:1px solid var(--line)}
.chip-role{display:block;font-size:10px;letter-spacing:.04em;text-transform:uppercase;margin-top:5px;color:var(--surface-ink,var(--ink));opacity:.72}
.chip code{font-size:10.5px;display:block;overflow:hidden;text-overflow:clip;white-space:nowrap}
@media (max-width:400px){.chips{grid-template-columns:repeat(3,minmax(0,1fr))}}
.facts{margin:0;display:grid;gap:4px;font-size:13px}
.facts div{display:grid;grid-template-columns:54px minmax(0,1fr);gap:8px;border-top:1px solid var(--line);padding-top:5px}
.facts dt{font-size:10px;letter-spacing:.06em;text-transform:uppercase;opacity:.72;padding-top:3px}
.facts dd{margin:0;overflow-wrap:anywhere}
.src{opacity:.72}
.pull{display:block;width:100%;text-align:left;margin:10px 0 0;padding:9px 10px;border:1px dashed var(--line);border-radius:min(var(--radius),8px);background:transparent;font-size:12px;overflow-wrap:anywhere;min-height:40px}
.pull .prompt{color:var(--accent);margin-right:4px}
details{margin-top:8px;font-size:13px}
summary{cursor:pointer;padding:8px 0;font-weight:600;min-height:36px}
.tokens{width:100%;border-collapse:collapse;font-size:12px;table-layout:fixed}
.tokens th,.tokens td{text-align:left;padding:5px 6px 5px 0;border-top:1px solid var(--line);vertical-align:top;font-weight:400;overflow-wrap:anywhere}
.tokens th{width:34%}.tokens td:nth-child(2){width:24%}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;border:1px solid var(--line);margin-right:6px;vertical-align:-1px}
.contrast,.extras,.warn{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:3px;font-size:12px}
.contrast b{font-family:var(--font-mono);font-weight:500;display:inline-block;min-width:44px}
.c-low b::after{content:" low"}.c-large b::after{content:" large only"}
.c-low b,.c-large b{min-width:0;margin-right:6px}
details h4{font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin:14px 0 4px;opacity:.8}
.empty{padding:40px 0;color:var(--muted)}

/* templates + method */
.sect{padding-top:44px;padding-bottom:44px;scroll-margin-top:12px}
.sect::before{content:"";display:block;border-top:1px solid var(--line);margin-bottom:40px}
.sect{padding-top:0}
.sect>p,.sect .lead{max-width:66ch}
.lead{color:var(--muted);margin:0 0 10px}
.starter{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:24px;margin:20px 0 8px;padding:20px;background:var(--surface);color:var(--surface-ink,var(--ink));border:1px solid var(--line);border-radius:min(var(--radius),16px)}
.starter h3{font:400 26px/1.1 var(--font-display);margin:0 0 8px}
.starter p{margin:0 0 12px}
.starter .btn{display:inline-flex;align-items:center;text-decoration:none;margin:0 8px 8px 0}
.starter .btn.quiet{background:var(--bg);color:var(--ink)}
.starter ol{margin:0;padding-left:20px}
@media (max-width:820px){.starter{grid-template-columns:minmax(0,1fr)}}
.tgroup{margin-top:34px}
.tgroup h3{font:400 24px/1.1 var(--font-display);margin:0 0 4px}
.repos{width:100%;border-collapse:collapse;font-size:14px}
.repos th,.repos td{text-align:left;padding:9px 12px 9px 0;border-top:1px solid var(--line);vertical-align:top;font-weight:400}
.repos thead th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);border-top:0}
.repos thead .num{font-family:var(--font-body);font-size:11px}
.repos tbody th a{font-weight:600}
.repos .num{text-align:right;white-space:nowrap;font-size:13px}
.repos .about{color:var(--muted);max-width:44ch}
.tag{display:inline-block;margin-left:8px;font:10px var(--font-mono);letter-spacing:.06em;text-transform:uppercase;border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:var(--muted)}
@media (max-width:760px){
  .repos thead{position:absolute;left:-9999px}
  .repos tr{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:2px 10px;padding:10px 0;border-top:1px solid var(--line)}
  .repos th,.repos td{border:0;padding:0}
  .repos tbody th,.repos .about{grid-column:1/-1}
  .repos .num{text-align:left}
  .repos td[data-label]::before{content:attr(data-label);display:block;font:10px var(--font-body);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
}
.steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;margin:20px 0 0;padding:0;list-style:none;border-top:1px solid var(--line)}
.steps li{padding:16px 16px 4px 0;border-right:1px solid var(--line)}
.steps li+li{padding-left:16px}.steps li:last-child{border-right:0}
.steps b{display:block;font:400 34px/1 var(--font-display);margin-bottom:6px}
.steps span{font-size:14px;color:var(--ink)}
@media (max-width:820px){.steps{grid-template-columns:repeat(2,minmax(0,1fr))}.steps li:nth-child(2){border-right:0}.steps li:nth-child(n+3){border-top:1px solid var(--line)}.steps li:nth-child(3){padding-left:0}}
.rules{margin:22px 0 0;padding-left:20px;max-width:70ch}
.rules li{margin:4px 0}
footer{border-top:1px solid var(--line);padding:22px 0 40px;font-size:13px;color:var(--muted)}
.toast{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:999px;font-size:13px;z-index:20;max-width:calc(100vw - 32px)}
"""

JS = r"""
(function () {
  var data = JSON.parse(document.getElementById('theme-data').textContent);
  var byId = {};
  data.themes.forEach(function (t) { byId[t.id] = t; });
  var root = document.documentElement;
  var loaded = {};
  var toastTimer;

  function loadFonts(theme) {
    if (!theme.web_url || loaded[theme.web_url]) return;
    loaded[theme.web_url] = true;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = theme.web_url;
    document.head.appendChild(link);
  }
  function setVars(node, theme, mode) {
    var colours = mode === 'dark' && theme.dark ? theme.dark : theme.colors;
    Object.keys(colours).forEach(function (role) {
      node.style.setProperty('--' + role.replace('_', '-'), colours[role]);
    });
    node.style.setProperty('--surface-ink', colours.surface_ink || colours.ink);
    node.style.setProperty('--font-display', theme.display);
    node.style.setProperty('--font-body', theme.body);
    node.style.setProperty('--font-mono', theme.mono);
    node.style.setProperty('--radius', theme.radius);
    return colours;
  }
  function toast(text) {
    var box = document.getElementById('toast');
    box.textContent = text;
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { box.hidden = true; }, 1800);
  }
  function copy(text, label) {
    function done() { window.__lastCopied = text; toast(label + ' copied'); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    } else { fallback(); }
    function fallback() {
      var area = document.createElement('textarea');
      area.value = text;
      document.body.appendChild(area);
      area.select();
      try { document.execCommand('copy'); } catch (err) {}
      area.remove();
      done();
    }
  }
  function wear(id, quiet) {
    var theme = byId[id] || byId[data.house];
    var card = document.getElementById(theme.id);
    var mode = card && card.dataset.mode === 'dark' ? 'dark' : 'light';
    loadFonts(theme);
    setVars(root, theme, mode);
    root.style.colorScheme = (mode === 'dark' || theme.scheme === 'dark') ? 'dark' : 'light';
    var worn = document.getElementById('worn');
    var isHouse = theme.id === data.house && mode === 'light';
    worn.hidden = isHouse;
    document.getElementById('worn-name').textContent = theme.name + (mode === 'dark' ? ' (dark set)' : '');
    document.getElementById('worn-cmd').dataset.copy = 'python theme.py pull ' + theme.id;
    document.querySelectorAll('[data-wear]').forEach(function (button) {
      var on = button.dataset.wear === theme.id && !isHouse;
      button.textContent = on ? 'Wearing' : 'Wear it';
      button.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if (!quiet) {
      var url = new URL(location.href);
      if (isHouse) { url.searchParams.delete('wear'); } else { url.searchParams.set('wear', theme.id); }
      history.replaceState(null, '', url);
    }
    root.dataset.worn = theme.id;
    document.querySelectorAll('a[data-carry]').forEach(function (link) {
      link.href = link.getAttribute('href').split('?')[0] + (isHouse ? '' : '?wear=' + theme.id);
    });
  }
  function setMode(card, mode) {
    var theme = byId[card.dataset.id];
    var colours = setVars(card, theme, mode);
    card.dataset.mode = mode;
    card.querySelectorAll('.mode-btn').forEach(function (button) {
      button.setAttribute('aria-pressed', button.dataset.mode === mode ? 'true' : 'false');
    });
    card.querySelectorAll('.chip').forEach(function (chip) {
      var role = chip.dataset.role;
      chip.dataset.copy = colours[role];
      chip.setAttribute('aria-label', 'Copy ' + role + ' ' + colours[role]);
      chip.querySelector('[data-swatch]').style.background = colours[role];
      chip.querySelector('[data-hex]').textContent = colours[role];
    });
    if (root.dataset.worn === theme.id) wear(theme.id);
  }

  document.addEventListener('click', function (event) {
    var target = event.target.closest('button');
    if (!target) return;
    if (target.dataset.wear) {
      wear(root.dataset.worn === target.dataset.wear ? data.house : target.dataset.wear);
    } else if (target.dataset.copyCss) {
      copy(byId[target.dataset.copyCss].css, byId[target.dataset.copyCss].name + ' CSS');
    } else if (target.dataset.copy) {
      copy(target.dataset.copy, target.dataset.copy.length > 30 ? 'Command' : target.dataset.copy);
    } else if (target.classList.contains('mode-btn')) {
      setMode(target.closest('.card'), target.dataset.mode);
    } else if (target.id === 'unwear') {
      wear(data.house);
    }
  });

  var state = { scheme: 'all', hue: 'all', text: '' };
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  function applyFilter() {
    var shown = 0;
    cards.forEach(function (card) {
      var okScheme = state.scheme === 'all' ||
        (state.scheme === 'both' ? card.dataset.dark === 'yes' : card.dataset.scheme === state.scheme);
      var okHue = state.hue === 'all' || card.dataset.hue === state.hue;
      var okText = !state.text || card.dataset.search.indexOf(state.text) !== -1;
      var show = okScheme && okHue && okText;
      card.hidden = !show;
      if (show) shown += 1;
    });
    document.getElementById('count').textContent = shown + ' of ' + cards.length;
    document.getElementById('empty').hidden = shown !== 0;
  }
  document.querySelectorAll('.pill').forEach(function (pill) {
    pill.addEventListener('click', function () {
      var group = pill.dataset.group;
      var same = state[group] === pill.dataset.value;
      state[group] = same ? 'all' : pill.dataset.value;
      document.querySelectorAll('.pill[data-group="' + group + '"]').forEach(function (other) {
        other.setAttribute('aria-pressed', other.dataset.value === state[group] ? 'true' : 'false');
      });
      applyFilter();
    });
  });
  document.getElementById('search').addEventListener('input', function (event) {
    state.text = event.target.value.trim().toLowerCase();
    applyFilter();
  });

  if ('IntersectionObserver' in window) {
    var watcher = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { loadFonts(byId[entry.target.dataset.id]); watcher.unobserve(entry.target); }
      });
    }, { rootMargin: '600px' });
    cards.forEach(function (card) { watcher.observe(card); });
  } else {
    data.themes.forEach(loadFonts);
  }
  var asked = new URL(location.href).searchParams.get('wear');
  if (asked && byId[asked]) { wear(asked, true); } else { root.dataset.worn = data.house; }
  applyFilter();
})();
"""


def page(themes, templates, stats, shelf):
    house = next(theme for theme in themes if theme["id"] == HOUSE_THEME)
    cards = "".join(card(theme, number) for number, theme in enumerate(themes, 1))
    payload = {
        "house": HOUSE_THEME,
        "themes": [
            {
                "id": theme["id"],
                "name": theme["name"],
                "scheme": theme["scheme"],
                "colors": theme["colors"],
                "dark": theme["dark"],
                "display": theme["fonts"]["display"],
                "body": theme["fonts"]["body"],
                "mono": theme["fonts"]["mono"],
                "radius": theme["radius"],
                "web_url": theme["fonts"]["web_url"],
                "css": B.theme_css(theme),
            }
            for theme in themes
        ],
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    hue_counts = {hue: sum(1 for theme in themes if theme["hue"] == hue) for hue in HUES}
    hue_sample = {}
    for theme in themes:
        hue_sample.setdefault(theme["hue"], theme["colors"]["accent"])
    hue_pills = "".join(
        f'<button type="button" class="pill" data-group="hue" data-value="{hue}" aria-pressed="false">'
        f'<span class="dot" style="background:{hue_sample[hue]}"></span>{hue} {hue_counts[hue]}</button>'
        for hue in HUES
        if hue_counts[hue]
    )
    light_count = sum(1 for theme in themes if theme["scheme"] == "light")
    dark_count = len(themes) - light_count
    both_count = sum(1 for theme in themes if theme["dark"])
    project_count = len({p["repo"] for theme in themes for p in theme["projects"]})
    checked = themes[0]["checked"]
    description = (
        f"{len(themes)} named themes read out of {project_count} shipped juw12 projects. "
        "One CSS file and one JSON file each, with contrast numbers and where every colour came from."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Themes: {len(themes)} looks from shipped projects, ready to pull</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="Themes: a specimen book of {len(themes)} shipped looks">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<link rel="canonical" href="{SITE_URL}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(house['fonts']['web_url'])}">
<style>
:root{{color-scheme:light;{style_vars(house['colors'], house['fonts'], house['radius'])}}}
{CSS}
</style>
</head>
<body>
<a class="skip" href="#specimens">Skip to the themes</a>
<header class="mast">
  <div class="wrap">
    <div class="mast-row">
      <p class="eyebrow"><a href="{REPO_URL}">juw12 / themes</a></p>
      <p class="eyebrow shelf-link"><a href="{SHELF_PAGE}" data-carry>Components: {shelf['count']} from React Bits</a></p>
      <p class="eyebrow">Checked {checked}</p>
    </div>
    <h1>{len(themes)} looks I already <em>shipped</em>, kept for the next app.</h1>
    <p class="standfirst">Each theme here was read out of a real project: its own CSS file, or the colours and fonts the
    live page actually paints. It got a name, one CSS file and one JSON file. Pull one in a line, or press
    <b>Wear it</b> on any card and this whole page changes into it.</p>
    <dl class="tally">
      <div><dt>Themes</dt><dd>{len(themes)}</dd></div>
      <div><dt>Projects behind them</dt><dd>{project_count}</dd></div>
      <div><dt>Light / dark ground</dt><dd>{light_count} / {dark_count}</dd></div>
      <div><dt>With a dark set too</dt><dd>{both_count}</dd></div>
    </dl>
  </div>
</header>
<main>
<section class="wrap how" aria-labelledby="how-h">
  <div>
    <h2 id="how-h">Pull one into a project</h2>
    <p>A theme is eleven custom properties: seven colours, three font stacks and a corner radius. Drop the file in,
    write your CSS against <code>var(--bg)</code>, <code>var(--accent)</code> and the rest, and the look follows.</p>
    <p><code>theme.py</code> is one file with no dependencies. It reads this folder first and falls back to GitHub.</p>
  </div>
  <div class="cmds">
    <button type="button" class="cmd" data-copy="python theme.py list"><span>python theme.py list</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="python theme.py pull {HOUSE_THEME} --to src/theme.css"><span>python theme.py pull {HOUSE_THEME} --to src/theme.css</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="curl -O {RAW_URL}/themes/{HOUSE_THEME}.css"><span>curl -O {RAW_URL}/themes/{HOUSE_THEME}.css</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="curl -O {RAW_URL}/theme.py"><span>curl -O {RAW_URL}/theme.py</span><span class="hint">copy</span></button>
  </div>
</section>
<section id="specimens" aria-label="Themes">
<div class="bar">
  <div class="wrap">
    <div class="bar-in">
      <input class="search" id="search" type="search" placeholder="Search a name, project or font" aria-label="Search themes">
      <div class="seg" role="group" aria-label="Ground">
        <button type="button" class="pill" data-group="scheme" data-value="light" aria-pressed="false">Light {light_count}</button>
        <button type="button" class="pill" data-group="scheme" data-value="dark" aria-pressed="false">Dark {dark_count}</button>
        <button type="button" class="pill" data-group="scheme" data-value="both" aria-pressed="false">Both sets {both_count}</button>
      </div>
      <div class="seg" role="group" aria-label="Accent colour">{hue_pills}</div>
      <span class="count" id="count" aria-live="polite">{len(themes)} of {len(themes)}</span>
    </div>
    <div class="worn" id="worn" hidden>
      <span>This page is wearing</span> <b id="worn-name"></b>
      <button type="button" id="worn-cmd" data-copy="">Copy pull command</button>
      <button type="button" id="unwear">Back to {esc(house['name'])}</button>
    </div>
  </div>
</div>
<div class="wrap">
  <div class="grid">{cards}</div>
  <p class="empty" id="empty" hidden>No theme matches. Clear the search or a filter.</p>
</div>
</section>
<section class="wrap sect" id="templates" aria-labelledby="tpl-h">
  <h2 id="tpl-h">Start from a template</h2>
  <p>A theme is only the paint. When a new app needs walls too, start from one of these.</p>
  <div class="starter">
    <div>
      <h3>The starter in this repo</h3>
      <p>One HTML page and one stylesheet that use nothing but the eleven tokens: a top bar, a list, a form,
      a table and buttons. Open it with any theme id to see that theme on a working screen.</p>
      <a class="btn primary" href="starter/?theme={HOUSE_THEME}">Open the starter</a>
      <a class="btn quiet" href="{REPO_URL}/generate">Use this repo as a template</a>
    </div>
    <ol>
      <li>Copy <code>starter/</code> into the new project.</li>
      <li>Run <code>python theme.py pull &lt;id&gt; --to starter/theme.css</code>.</li>
      <li>Build on <code>app.css</code>. It never names a colour, only a token.</li>
    </ol>
  </div>
  <p class="lead">Below: {sum(len(group['repos']) for group in templates['groups'])} public repos worth starting from,
  sorted by star count. Star count, licence and last push were read from the GitHub API on {esc(templates['checked'])};
  the last column is the repo's own description, shortened.</p>
  {template_section(templates)}
</section>
<section class="wrap sect" id="method" aria-labelledby="method-h">
  <h2 id="method-h">How a theme gets in</h2>
  <ol class="steps">
    <li><b>{stats['scanned']}</b><span>of my own repos scanned for the files that define a look: design notes, CSS, the main page.</span></li>
    <li><b>{stats['with_look']}</b><span>had a look of their own. The rest are scripts, data or research with no interface.</span></li>
    <li><b>{stats['rendered']}</b><span>live pages opened in a browser, light and dark, to read what is really painted.</span></li>
    <li><b>{len(themes)}</b><span>themes after projects that share one look were merged and private work was left out.</span></li>
  </ol>
  <ul class="rules">
    <li>No colour is made up. Every value is in the project's CSS or on its page, or it is marked <i>derived</i> with the rule used.</li>
    <li>Where the scan guessed wrong it was fixed by hand, and the reason is written on the card.</li>
    <li>Contrast numbers are computed (WCAG 2 ratio), and anything under 4.5:1 for text is flagged, not hidden.</li>
    <li>System fonts stay system fonts. Web fonts are named only when the project loads them.</li>
  </ul>
</section>
</main>
<footer>
  <div class="wrap">Tokens and code are MIT licensed. The fonts named belong to their makers; check each licence before shipping.
  Source and build scripts: <a href="{REPO_URL}">github.com/juw12/themes</a>.</div>
</footer>
<div class="toast" id="toast" role="status" hidden></div>
<script type="application/json" id="theme-data">{data_json}</script>
<script>{JS}</script>
</body>
</html>
"""


SHELF_CSS = r"""
.mast h1{max-width:16ch}
.back{color:var(--accent);font-weight:600}
.credit{max-width:70ch;color:var(--muted);font-size:14px;margin:0 0 26px}
.bar-in label{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.picker{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.wearer{height:44px;max-width:100%;padding:0 10px;border:1px solid var(--line);border-radius:min(var(--radius),12px);background:var(--surface);color:var(--surface-ink,var(--ink));font:16px var(--font-body)}
.shelf{padding-top:28px}
.shelf h2{font:400 clamp(26px,3vw,36px)/1.1 var(--font-display);margin:0;letter-spacing:-.01em;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
.shelf h2 span{font:12px var(--font-mono);color:var(--muted)}
.shelf .grid{padding:18px 0 12px;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:16px}
.part .name{font-size:clamp(24px,2.1vw,28px);margin:8px 0 6px}
.part .note{min-height:3em;margin-bottom:10px}
.part .deps{margin:0 0 12px;font-size:12px;color:var(--muted);overflow-wrap:anywhere}
.part .deps code{color:var(--ink)}
.part .actions{margin:auto 0 0}
.part a.link{text-decoration:none;display:inline-flex;align-items:center;min-height:40px}
.part a.link:hover{text-decoration:underline}
.part .pull{margin-top:10px;min-height:66px}
.extra{list-style:none;padding:0;margin:14px 0 0;display:grid;gap:10px;max-width:70ch}
.extra li{border-top:1px solid var(--line);padding-top:10px}
.extra .btn{margin-top:8px}
.part .no,.bar-in label{font-size:12px}
.mast-row{align-items:center}
.eyebrow a{padding:16px 0}
@media (pointer:coarse){.pill{height:48px;padding:0 14px}.btn,.part a.link,.cmd{min-height:48px}.part a.link{padding:0 8px}.search,.wearer{height:48px}}
"""

SHELF_JS = r"""
(function () {
  var data = JSON.parse(document.getElementById('shelf-data').textContent);
  var root = document.documentElement;
  var byId = {};
  data.themes.forEach(function (t) { byId[t.id] = t; });
  var loaded = {};
  var toastTimer;
  var state = { category: 'all', text: '', lang: 'TS', style: 'TW' };

  function flavor() { return state.lang + '-' + state.style; }
  function command(name) { return data.install.replace('{name}', name).replace('{flavor}', flavor()); }
  function toast(text) {
    var box = document.getElementById('toast');
    box.textContent = text;
    box.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { box.hidden = true; }, 1800);
  }
  function copy(text, label) {
    function done() { window.__lastCopied = text; toast(label + ' copied'); }
    function fallback() {
      var area = document.createElement('textarea');
      area.value = text;
      document.body.appendChild(area);
      area.select();
      try { document.execCommand('copy'); } catch (err) {}
      area.remove();
      done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else { fallback(); }
  }
  function wear(id, quiet) {
    var theme = byId[id] || byId[data.house];
    if (theme.web_url && !loaded[theme.web_url]) {
      loaded[theme.web_url] = true;
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = theme.web_url;
      document.head.appendChild(link);
    }
    Object.keys(theme.colors).forEach(function (role) {
      root.style.setProperty('--' + role.replace('_', '-'), theme.colors[role]);
    });
    root.style.setProperty('--surface-ink', theme.colors.surface_ink || theme.colors.ink);
    root.style.setProperty('--font-display', theme.display);
    root.style.setProperty('--font-body', theme.body);
    root.style.setProperty('--font-mono', theme.mono);
    root.style.setProperty('--radius', theme.radius);
    root.style.colorScheme = theme.scheme === 'dark' ? 'dark' : 'light';
    root.dataset.worn = theme.id;
    document.getElementById('wearer').value = theme.id;
    var isHouse = theme.id === data.house;
    document.querySelectorAll('a[data-carry]').forEach(function (link) {
      link.href = link.getAttribute('href').split('?')[0] + (isHouse ? '' : '?wear=' + theme.id);
    });
    if (!quiet) {
      var url = new URL(location.href);
      if (isHouse) { url.searchParams.delete('wear'); } else { url.searchParams.set('wear', theme.id); }
      history.replaceState(null, '', url);
    }
  }
  function refreshCommands() {
    document.querySelectorAll('[data-add]').forEach(function (button) {
      var text = command(button.dataset.add);
      button.dataset.copy = text;
      var shown = button.querySelector('[data-cmd]');
      if (shown) shown.textContent = text;
    });
  }

  var cards = Array.prototype.slice.call(document.querySelectorAll('.part'));
  var sections = Array.prototype.slice.call(document.querySelectorAll('.shelf[data-category]'));
  function applyFilter() {
    var shown = 0;
    cards.forEach(function (card) {
      var show = (state.category === 'all' || card.dataset.category === state.category) &&
        (!state.text || card.dataset.search.indexOf(state.text) !== -1);
      card.hidden = !show;
      if (show) shown += 1;
    });
    sections.forEach(function (section) {
      section.hidden = !section.querySelector('.part:not([hidden])');
    });
    document.getElementById('count').textContent = shown + ' of ' + cards.length;
    document.getElementById('empty').hidden = shown !== 0;
  }

  document.addEventListener('click', function (event) {
    var target = event.target.closest('button');
    if (!target) return;
    if (target.dataset.copy) {
      copy(target.dataset.copy, 'Install command');
    } else if (target.classList.contains('pill')) {
      var group = target.dataset.group;
      var value = target.dataset.value;
      if (group === 'category') { state.category = state.category === value ? 'all' : value; } else { state[group] = value; }
      document.querySelectorAll('.pill[data-group="' + group + '"]').forEach(function (other) {
        other.setAttribute('aria-pressed', other.dataset.value === state[group] ? 'true' : 'false');
      });
      if (group === 'category') { applyFilter(); } else { refreshCommands(); }
    }
  });
  document.getElementById('search').addEventListener('input', function (event) {
    state.text = event.target.value.trim().toLowerCase();
    applyFilter();
  });
  document.getElementById('wearer').addEventListener('change', function (event) { wear(event.target.value); });

  var asked = new URL(location.href).searchParams.get('wear');
  if (asked && byId[asked]) { wear(asked, true); } else { root.dataset.worn = data.house; }
  refreshCommands();
  applyFilter();
})();
"""


def shelf_command(shelf, name, flavor=None):
    return shelf["install"]["shadcn"].format(name=name, flavor=flavor or shelf["default_flavor"])


def shelf_card(shelf, row, category_name):
    deps = (
        "Brings " + ", ".join(f"<code>{esc(dep)}</code>" for dep in row["dependencies"])
        if row["dependencies"]
        else "No extra package"
    )
    command = shelf_command(shelf, row["name"])
    search = " ".join([row["name"], row["title"], category_name, row["description"]] + row["dependencies"]).lower()
    return (
        f'<article class="card part" id="{esc(row["id"])}" data-category="{esc(row["category"])}" data-search="{esc(search)}">'
        f'<div class="card-top"><span class="no">{esc(category_name)}</span></div>'
        f'<h3 class="name">{esc(row["title"])}</h3>'
        f'<p class="note">{esc(row["description"])}</p>'
        f'<p class="deps">{deps}</p>'
        '<div class="actions">'
        f'<button type="button" class="btn primary" data-add="{esc(row["name"])}" data-copy="{esc(command)}">Copy install command</button>'
        f'<a class="link" href="{esc(row["demo"])}" target="_blank" rel="noopener">See it live</a>'
        "</div>"
        f'<button type="button" class="pull" data-add="{esc(row["name"])}" data-copy="{esc(command)}" '
        f'aria-label="Copy the install command for {esc(row["title"])}"><span class="prompt">$</span><span data-cmd>{esc(command)}</span></button>'
        "</article>"
    )


def shelf_page(themes, shelf):
    house = next(theme for theme in themes if theme["id"] == HOUSE_THEME)
    source = shelf["read_from"]
    names = {row["id"]: row["name"] for row in shelf["categories"]}
    sections = []
    for category in shelf["categories"]:
        cards = "".join(
            shelf_card(shelf, row, category["name"]) for row in shelf["components"] if row["category"] == category["id"]
        )
        sections.append(
            f'<section class="wrap shelf" data-category="{category["id"]}" aria-labelledby="h-{category["id"]}">'
            f'<h2 id="h-{category["id"]}">{esc(category["name"])} <span>{category["count"]}</span></h2>'
            f'<div class="grid">{cards}</div></section>'
        )
    extra = "".join(
        f'<li><b>{esc(row["name"])}</b>: {esc(row["description"])}<br>'
        f'<button type="button" class="btn quiet" data-add="{esc(row["name"])}" data-copy="{esc(shelf_command(shelf, row["name"]))}">'
        "Copy install command</button></li>"
        for row in shelf["unlisted"]
    )
    extra_block = (
        '<section class="wrap sect" aria-labelledby="extra-h"><h2 id="extra-h">In their registry, without a demo page</h2>'
        f'<p class="lead">{len(shelf["unlisted"])} more can be installed by name. They are not in the React Bits menu, '
        f'so there is nothing to see first.</p><ul class="extra">{extra}</ul></section>'
        if shelf["unlisted"]
        else ""
    )
    category_pills = "".join(
        f'<button type="button" class="pill" data-group="category" data-value="{row["id"]}" aria-pressed="false">'
        f'{esc(row["name"])} {row["count"]}</button>'
        for row in shelf["categories"]
    )
    options = "".join(
        f'<option value="{esc(theme["id"])}"{" selected" if theme["id"] == HOUSE_THEME else ""}>{esc(theme["name"])}</option>'
        for theme in themes
    )
    payload = {
        "house": HOUSE_THEME,
        "install": shelf["install"]["shadcn"],
        "themes": [
            {
                "id": theme["id"],
                "name": theme["name"],
                "scheme": theme["scheme"],
                "colors": theme["colors"],
                "display": theme["fonts"]["display"],
                "body": theme["fonts"]["body"],
                "mono": theme["fonts"]["mono"],
                "radius": theme["radius"],
                "web_url": theme["fonts"]["web_url"],
            }
            for theme in themes
        ],
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    count = shelf["count"]
    description = (
        f"A catalogue of the {count} free React Bits components in {len(shelf['categories'])} groups: what each one does, "
        "what it needs, where to see it and the one line that installs it. No component source is kept here."
    )
    page_url = SITE_URL + SHELF_PAGE
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Components: {count} React Bits parts, catalogued for the next app</title>
<meta name="description" content="{esc(description)}">
<meta property="og:title" content="Components: {count} React Bits parts next to the themes">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{page_url}">
<link rel="canonical" href="{page_url}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(house['fonts']['web_url'])}">
<style>
:root{{color-scheme:light;{style_vars(house['colors'], house['fonts'], house['radius'])}}}
{CSS}
{SHELF_CSS}
</style>
</head>
<body>
<a class="skip" href="#parts">Skip to the components</a>
<header class="mast">
  <div class="wrap">
    <div class="mast-row">
      <p class="eyebrow"><a href="{REPO_URL}">juw12 / themes</a></p>
      <p class="eyebrow shelf-link"><a class="back" href="./" data-carry>Back to the {len(themes)} themes</a></p>
      <p class="eyebrow">Read {esc(source['read'])}</p>
    </div>
    <h1>{count} moving parts by React Bits, <em>catalogued</em>.</h1>
    <p class="standfirst">The second shelf. A theme is the paint; these are parts that move: text effects, cursors,
    cards, small controls and whole animated backgrounds. Each card says what the part does, what it needs,
    where to see it running, and the one line that puts it into an app.</p>
    <p class="credit"><a href="{esc(source['site'])}">React Bits</a> is made by {esc(source['author'])} and is free to use
    in an app, also a paid one. Its licence (<a href="{esc(source['licence_url'])}">{esc(source['licence'])}</a>) does not
    allow handing the components on, so none of their code, sounds or demos is kept in this library. The install line
    pulls a part straight from reactbits.dev into your project.</p>
    <dl class="tally">
      <div><dt>Components</dt><dd>{count}</dd></div>
      <div><dt>Groups</dt><dd>{len(shelf['categories'])}</dd></div>
      <div><dt>Flavours each</dt><dd>{len(shelf['flavors'])}</dd></div>
      <div><dt>Their code kept here</dt><dd>None</dd></div>
    </dl>
  </div>
</header>
<main>
<section class="wrap how" aria-labelledby="how-h">
  <div>
    <h2 id="how-h">Add one to a project</h2>
    <p>Pick the flavour your app is written in, press <b>Copy install command</b> on a card and run it in the
    project folder. It needs Node.js and works in any React or Next.js app.</p>
    <p><code>theme.py</code> does the same from a terminal, and can name a theme's colours to pass as props.</p>
  </div>
  <div class="cmds">
    <button type="button" class="cmd" data-copy="python theme.py components list --category backgrounds"><span>python theme.py components list --category backgrounds</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="python theme.py components add SplitText --flavor TS-TW"><span>python theme.py components add SplitText --flavor TS-TW</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="python theme.py components add Aurora --theme {HOUSE_THEME} --run"><span>python theme.py components add Aurora --theme {HOUSE_THEME} --run</span><span class="hint">copy</span></button>
    <button type="button" class="cmd" data-copy="curl -O {RAW_URL}/theme.py"><span>curl -O {RAW_URL}/theme.py</span><span class="hint">copy</span></button>
  </div>
</section>
<section id="parts" aria-label="Components">
<div class="bar">
  <div class="wrap">
    <div class="bar-in">
      <input class="search" id="search" type="search" placeholder="Search a name, what it does or a package" aria-label="Search components">
      <div class="seg" role="group" aria-label="Group">{category_pills}</div>
      <span class="count" id="count" aria-live="polite">{count} of {count}</span>
    </div>
    <div class="bar-in">
      <div class="picker" role="group" aria-label="Language">
        <label>Language</label>
        <div class="seg">
          <button type="button" class="pill" data-group="lang" data-value="TS" aria-pressed="true">TypeScript</button>
          <button type="button" class="pill" data-group="lang" data-value="JS" aria-pressed="false">JavaScript</button>
        </div>
      </div>
      <div class="picker" role="group" aria-label="Styling">
        <label>Styling</label>
        <div class="seg">
          <button type="button" class="pill" data-group="style" data-value="TW" aria-pressed="true">Tailwind</button>
          <button type="button" class="pill" data-group="style" data-value="CSS" aria-pressed="false">Plain CSS</button>
        </div>
      </div>
      <div class="picker">
        <label for="wearer">This page wears</label>
        <select class="wearer" id="wearer">{options}</select>
      </div>
    </div>
  </div>
</div>
{''.join(sections)}
<div class="wrap"><p class="empty" id="empty" hidden>No component matches. Clear the search or the group.</p></div>
</section>
{extra_block}
</main>
<footer>
  <div class="wrap">Components by {esc(source['author'])}, <a href="{esc(source['licence_url'])}">{esc(source['licence'])}</a>.
  This page lists facts read from <a href="{esc(source['site'])}">reactbits.dev</a> on {esc(source['read'])}; their code is not copied here.
  React Bits Pro is a separate paid product and is not listed. Source and build scripts:
  <a href="{REPO_URL}">github.com/juw12/themes</a>.</div>
</footer>
<div class="toast" id="toast" role="status" hidden></div>
<script type="application/json" id="shelf-data">{data_json}</script>
<script>{SHELF_JS}</script>
</body>
</html>
"""


def shelf_readme(shelf):
    source = shelf["read_from"]
    per = ", ".join(f"{row['name']} {row['count']}" for row in shelf["categories"])
    extra = (
        f" {len(shelf['unlisted'])} more ({', '.join(row['name'] for row in shelf['unlisted'])}) are in their registry "
        "without a demo page; `components add` knows them too."
        if shelf["unlisted"]
        else ""
    )
    return f"""## React Bits components

The second shelf: a catalogue of the {shelf['count']} free [React Bits]({source['site']}) components ({per}),
read from their registry on {source['read']}.{extra}
Browse them: **{SITE_URL}{SHELF_PAGE}**

```
python theme.py components list --category backgrounds
python theme.py components list --search cursor
python theme.py components add SplitText --flavor TS-TW          # prints the command and what it brings
python theme.py components add Aurora --theme cairn-paper --run   # runs it here, names the theme's colours
```

`add` prints one of these, for the flavour asked (`JS-CSS`, `JS-TW`, `TS-CSS`, `TS-TW`):

```
npx shadcn@latest add {source['site']}/r/SplitText-TS-TW.json
npx jsrepo@latest add {source['site']}/r/SplitText-TS-TW
```

React Bits is by {source['author']}, licensed [{source['licence']}]({source['licence_url']}): free to use in an app,
not to be handed on. So this repo keeps a list of facts (`reactbits.json`: name, group, description, packages, demo
page) and none of their code, sounds or demo media. A component is pulled from reactbits.dev at the moment you add
it. React Bits Pro is a separate paid product and is not listed. `python tools/reactbits.py` reads the list again.
"""


def shelf_templates_md(shelf):
    source = shelf["read_from"]
    lines = [
        "",
        "## Parts that move: React Bits",
        "",
        f"{shelf['count']} free animated React components by {source['author']} ([{source['licence']}]({source['licence_url']})), "
        f"catalogued in this repo without their code: [{SITE_URL}{SHELF_PAGE}]({SITE_URL}{SHELF_PAGE}). "
        "`python theme.py components add <Name>` prints the line that installs one.",
        "",
        "| Group | Components | Browse |",
        "|---|---:|---|",
    ]
    for row in shelf["categories"]:
        lines.append(f"| {row['name']} | {row['count']} | [{source['site']}/c/{row['id']}]({source['site']}/c/{row['id']}) |")
    return "\n".join(lines) + "\n"


def readme(themes, templates, shelf):
    rows = "\n".join(
        f"| [{theme['name']}]({SITE_URL}#{theme['id']}) | `{theme['id']}` | {theme['scheme']}"
        f"{' + dark' if theme['dark'] else ''} | `{theme['colors']['bg']}` `{theme['colors']['ink']}` "
        f"`{theme['colors']['accent']}` | {B.first_family(theme['fonts']['display'])} | "
        f"{', '.join(p['repo'] for p in theme['projects'])} |"
        for theme in themes
    )
    return f"""# themes

{len(themes)} named themes, read out of projects I already shipped, kept in one place so the next app can start
from a look that is known to work.

Browse them: **{SITE_URL}** (press *Wear it* on a card and the page changes into that theme).

## Pull a theme

```
curl -O {RAW_URL}/theme.py
python theme.py list
python theme.py pull cairn-paper --to src/theme.css
python theme.py pull vow-brick --format json
python theme.py pull riak-tidepool --design-md      # a design.md to hand to an AI or a teammate
```

`theme.py` needs only Python 3.8+. It reads the `themes/` folder next to it and falls back to this repo on GitHub.
Without Python: `curl -O {RAW_URL}/themes/<id>.css`.

## What a theme is

One CSS file and one JSON file per theme, in `themes/`.

```css
:root {{
  --bg  --surface  --ink  --muted  --line  --accent  --accent-ink   /* seven colours */
  --font-display  --font-body  --font-mono                          /* three font stacks */
  --radius                                                          /* one corner radius */
}}
```

Optional extras: `--ok`, `--warn`, `--bad`, `--accent2`, `--surface-ink`, and project colours as `--x-<name>`.
Themes with a dark set add it under `@media (prefers-color-scheme: dark)`.

The JSON file also carries: which projects the theme came from, where each colour was read from, which values
were derived (and how), contrast ratios, and warnings where text contrast is under 4.5:1.

## The rules

- No colour is made up. `tools/build.py` stops if a colour is not in the project's CSS or on its rendered page.
- A hand fix needs a written reason in `src/curation.json`; the reason is shown on the theme's card.
- Contrast is computed, never typed in.
- `python tools/check.py` runs every gate (schema, provenance, contrast, text hygiene, page checks, and that
  the components shelf holds facts only).

## Start a new app from it

This repo is a GitHub template: **Use this template** gives you the `starter/` app (one HTML page, one stylesheet
that only uses the tokens) plus every theme. [TEMPLATES.md](TEMPLATES.md) lists
{sum(len(group['repos']) for group in templates['groups'])} well-known public repos to start an app's design from,
with stars, licence and last push as of {templates['checked']}.

{shelf_readme(shelf)}
## All themes

| Theme | id | Ground | bg / ink / accent | Display face | From |
|---|---|---|---|---|---|
{rows}

## Rebuild

```
python tools/build.py     # src/merged.json + src/curation.json -> themes/, themes.json
python tools/reactbits.py # reactbits.dev -> src/reactbits.json, reactbits.json (facts only, no source)
python tools/site.py      # index.html, components.html, README.md, TEMPLATES.md
python tools/check.py     # gates
```

`tools/scan.py`, `tools/extract.py`, `tools/probe_live.py` and `tools/reconcile.py` are the scripts that read the
projects in the first place (they need the GitHub CLI and Playwright).

## Licence

MIT for the tokens and the code. Fonts named in a theme belong to their makers; check each font's licence.
"""


def templates_md(templates, shelf):
    parts = [
        "# Templates to start an app's design from",
        "",
        f"Star count, licence and last push were read from the GitHub API on {templates['checked']}. "
        "The last column is the repo's own description. Sorted by stars inside each group.",
        "",
        "The closest starting point is this repo itself: press **Use this template** on GitHub, then see `starter/`.",
    ]
    for group in templates["groups"]:
        parts += ["", f"## {group['title']}", "", group["lead"], "", "| Repo | GitHub stars | Licence | Last push | In its own words |", "|---|---:|---|---|---|"]
        for row in group["repos"]:
            mark = " (template repo)" if row["template"] else ""
            about = row["about"].replace("|", "/")
            parts.append(
                f"| [{row['repo']}]({row['url']}){mark} | {row['stars']:,} | {row['licence']} | {row['pushed']} | {about} |"
            )
    return "\n".join(parts) + "\n" + shelf_templates_md(shelf)


def main():
    themes = [B.load_json(os.path.join(ROOT, "themes", entry["id"] + ".json"))
              for entry in B.load_json(os.path.join(ROOT, "themes.json"))["themes"]]
    templates = B.load_json(os.path.join(ROOT, "src", "templates.json"))
    stats = B.load_json(STATS_FILE)
    shelf = B.load_json(SHELF_FILE)
    B.write(os.path.join(ROOT, "index.html"), page(themes, templates, stats, shelf))
    B.write(os.path.join(ROOT, SHELF_PAGE), shelf_page(themes, shelf))
    B.write(os.path.join(ROOT, "README.md"), readme(themes, templates, shelf))
    B.write(os.path.join(ROOT, "TEMPLATES.md"), templates_md(templates, shelf))
    print(f"wrote index.html ({len(themes)} cards), {SHELF_PAGE} ({shelf['count']} cards), README.md, TEMPLATES.md")


if __name__ == "__main__":
    main()
