# themes

56 named themes, read out of projects I already shipped, kept in one place so the next app can start
from a look that is known to work.

Browse them: **https://juw12.github.io/themes/** (press *Wear it* on a card and the page changes into that theme).

## Pull a theme

```
curl -O https://raw.githubusercontent.com/juw12/themes/main/theme.py
python theme.py list
python theme.py pull cairn-paper --to src/theme.css
python theme.py pull vow-brick --format json
python theme.py pull riak-tidepool --design-md      # a design.md to hand to an AI or a teammate
```

`theme.py` needs only Python 3.8+. It reads the `themes/` folder next to it and falls back to this repo on GitHub.
Without Python: `curl -O https://raw.githubusercontent.com/juw12/themes/main/themes/<id>.css`.

## What a theme is

One CSS file and one JSON file per theme, in `themes/`.

```css
:root {
  --bg  --surface  --ink  --muted  --line  --accent  --accent-ink   /* seven colours */
  --font-display  --font-body  --font-mono                          /* three font stacks */
  --radius                                                          /* one corner radius */
}
```

Optional extras: `--ok`, `--warn`, `--bad`, `--accent2`, `--surface-ink`, and project colours as `--x-<name>`.
Themes with a dark set add it under `@media (prefers-color-scheme: dark)`.

The JSON file also carries: which projects the theme came from, where each colour was read from, which values
were derived (and how), contrast ratios, and warnings where text contrast is under 4.5:1.

## The rules

- No colour is made up. `tools/build.py` stops if a colour is not in the project's CSS or on its rendered page.
- A hand fix needs a written reason in `src/curation.json`; the reason is shown on the theme's card.
- Contrast is computed, never typed in.
- `python tools/check.py` runs every gate (schema, provenance, contrast, text hygiene, page checks).

## Start a new app from it

This repo is a GitHub template: **Use this template** gives you the `starter/` app (one HTML page, one stylesheet
that only uses the tokens) plus every theme. [TEMPLATES.md](TEMPLATES.md) lists
40 well-known public repos to start an app's design from,
with stars, licence and last push as of 2026-11-20.

## All themes

| Theme | id | Ground | bg / ink / accent | Display face | From |
|---|---|---|---|---|---|
| [Cairn Paper](https://juw12.github.io/themes/#cairn-paper) | `cairn-paper` | light + dark | `#f4f1ea` `#1b1a17` `#d9481f` | Instrument Serif | cairn, bits-and-tickers, founder-studio |
| [Titip Counter Blue](https://juw12.github.io/themes/#titip-counter-blue) | `titip-counter-blue` | light + dark | `#f4f1ea` `#1b1a17` `#2f5b8c` | Instrument Serif | titip |
| [Relay Slate](https://juw12.github.io/themes/#relay-slate) | `relay-slate` | light + dark | `#f4f1ea` `#1b1a17` `#2f5b8c` | -apple-system | vector-relay |
| [Reachpilot Dispatch](https://juw12.github.io/themes/#reachpilot-dispatch) | `reachpilot-dispatch` | light | `#f4f1ea` `#1b1a17` `#0a5aa8` | Instrument Serif | reachpilot |
| [Morrow Broadsheet](https://juw12.github.io/themes/#morrow-broadsheet) | `morrow-broadsheet` | light + dark | `#f7f6f2` `#14161a` `#b4232c` | system-ui | morrow |
| [Earlystar Zinc](https://juw12.github.io/themes/#earlystar-zinc) | `earlystar-zinc` | light + dark | `#fafafa` `#09090b` `#4f46e5` | Inter | earlystar, nudge |
| [Portfolio Cobalt](https://juw12.github.io/themes/#portfolio-cobalt) | `portfolio-cobalt` | light + dark | `#ffffff` `#0f172a` `#1f5eff` | Inter | portfolio, juw12.github.io |
| [Lelet Ember](https://juw12.github.io/themes/#lelet-ember) | `lelet-ember` | light + dark | `#f4efe6` `#1b1a17` `#d9381e` | Iowan Old Style | lelet |
| [Index Card Indigo](https://juw12.github.io/themes/#index-card-indigo) | `index-card-indigo` | light | `#f7f8fb` `#101828` `#4f46e5` | -apple-system | projects |
| [Buddy Tangerine](https://juw12.github.io/themes/#buddy-tangerine) | `buddy-tangerine` | light | `#fffaf4` `#1f2130` `#ff8424` | Bricolage Grotesque | buddy |
| [Lineup Scorecard](https://juw12.github.io/themes/#lineup-scorecard) | `lineup-scorecard` | light + dark | `#f6f3ec` `#1d1b16` `#c2500f` | Georgia | lineup |
| [Hoki Temple Gold](https://juw12.github.io/themes/#hoki-temple-gold) | `hoki-temple-gold` | light + dark | `#f6f2eb` `#26221d` `#8a6418` | Iowan Old Style | hoki |
| [Saver Pine](https://juw12.github.io/themes/#saver-pine) | `saver-pine` | light + dark | `#f5f3ee` `#1d1c1a` `#2f5d50` | -apple-system | social-saver |
| [Eco Terminal](https://juw12.github.io/themes/#eco-terminal) | `eco-terminal` | dark | `#0f1412` `#e6ece8` `#22aa55` | Segoe UI | cpu-eco-toggle |
| [Inti Night Amber](https://juw12.github.io/themes/#inti-night-amber) | `inti-night-amber` | dark | `#0e1116` `#e6e9ee` `#f2b34a` | system-ui | inti |
| [Kemudi Helm](https://juw12.github.io/themes/#kemudi-helm) | `kemudi-helm` | light | `#f5f2ea` `#1c1b19` `#0d6b63` | Georgia | kemudi |
| [Steward Blue](https://juw12.github.io/themes/#steward-blue) | `steward-blue` | light + dark | `#f4f6fb` `#172033` `#1f6fd1` | Segoe UI | steward, hexbane |
| [Vera Noir](https://juw12.github.io/themes/#vera-noir) | `vera-noir` | dark | `#14130f` `#f3efe6` `#ffb020` | Georgia | not-real-vera |
| [Kilat Flash](https://juw12.github.io/themes/#kilat-flash) | `kilat-flash` | light + dark | `#fbfaf7` `#1c1b19` `#b45309` | Cascadia Code | kilat |
| [Trunnion Workshop](https://juw12.github.io/themes/#trunnion-workshop) | `trunnion-workshop` | light | `#f3f4f5` `#15181c` `#b3460e` | IBM Plex Sans Condensed | trunnion-topopt |
| [Telisik Case File](https://juw12.github.io/themes/#telisik-case-file) | `telisik-case-file` | light + dark | `#fbfbf8` `#16181d` `#c8321f` | Iowan Old Style | telisik |
| [Tolstack Blueprint](https://juw12.github.io/themes/#tolstack-blueprint) | `tolstack-blueprint` | dark | `#0c1a2b` `#e5eef8` `#c2410c` | Roboto Slab | tolstack |
| [Gate Ledger](https://juw12.github.io/themes/#gate-ledger) | `gate-ledger` | light | `#f7f5ef` `#1c1d21` `#0f6b3a` | Source Serif 4 | gate |
| [Lahap Sambal](https://juw12.github.io/themes/#lahap-sambal) | `lahap-sambal` | light | `#f5efe3` `#1d1813` `#b4380f` | Iowan Old Style | lahap |
| [Precedent Casebook](https://juw12.github.io/themes/#precedent-casebook) | `precedent-casebook` | light | `#fffaf3` `#1f2330` `#8c2f1b` | Libre Caslon Display | precedent |
| [Batam Harbour](https://juw12.github.io/themes/#batam-harbour) | `batam-harbour` | light | `#f4f5f7` `#0f172a` `#0b3b5c` | Instrument Serif | batam-uncle-says |
| [Tagalong Trail](https://juw12.github.io/themes/#tagalong-trail) | `tagalong-trail` | light + dark | `#f5f0e6` `#1e1b16` `#b93a1e` | Iowan Old Style | tagalong |
| [Jeda Brass](https://juw12.github.io/themes/#jeda-brass) | `jeda-brass` | light | `#f6f2eb` `#26221d` `#b8862b` | Iowan Old Style | jeda |
| [MCP Report Red](https://juw12.github.io/themes/#mcp-report-red) | `mcp-report-red` | light | `#ffffff` `#1a1a1e` `#d70015` | -apple-system | state-of-mcp-servers |
| [Pocketdex Red](https://juw12.github.io/themes/#pocketdex-red) | `pocketdex-red` | light | `#f6f2eb` `#26221d` `#c0432f` | Iowan Old Style | pocketdex |
| [Millennium Violet](https://juw12.github.io/themes/#millennium-violet) | `millennium-violet` | light | `#fbfaf7` `#1c2230` `#6d3fd1` | Segoe UI | millennium-digest |
| [Nadaku Songbook](https://juw12.github.io/themes/#nadaku-songbook) | `nadaku-songbook` | light + dark | `#efe8da` `#2a2521` `#a8321f` | Source Serif 4 | nadaku |
| [Scentvec Plum](https://juw12.github.io/themes/#scentvec-plum) | `scentvec-plum` | light + dark | `#faf6f0` `#221a1f` `#7a2e5a` | Iowan Old Style | scentvec |
| [Blame Midnight Gold](https://juw12.github.io/themes/#blame-midnight-gold) | `blame-midnight-gold` | dark | `#0a0f1f` `#eef1f8` `#f2c14e` | system-ui | mlbb-blame |
| [Jepret Shutter](https://juw12.github.io/themes/#jepret-shutter) | `jepret-shutter` | light + dark | `#f5f1ea` `#1d1b18` `#c43d22` | system-ui | jepret |
| [Ruang Terracotta](https://juw12.github.io/themes/#ruang-terracotta) | `ruang-terracotta` | light + dark | `#f4f1ea` `#1e2328` `#a84b25` | Iowan Old Style | ruang |
| [Bilas Enamel](https://juw12.github.io/themes/#bilas-enamel) | `bilas-enamel` | light + dark | `#e9e4d8` `#1d2629` `#c8442c` | Bahnschrift | bilas |
| [Reda Still Teal](https://juw12.github.io/themes/#reda-still-teal) | `reda-still-teal` | light + dark | `#f6f1ea` `#231e1a` `#1f5f55` | Charter | reda |
| [Riak Tidepool](https://juw12.github.io/themes/#riak-tidepool) | `riak-tidepool` | light + dark | `#f5f0e7` `#1d2a27` `#1f5f4a` | Fraunces | riak |
| [Vale Shardlight](https://juw12.github.io/themes/#vale-shardlight) | `vale-shardlight` | dark | `#050d0a` `#e8efe5` `#5fe0ff` | Cormorant Garamond | vale |
| [Vow Brick](https://juw12.github.io/themes/#vow-brick) | `vow-brick` | light + dark | `#f7f3ea` `#1d1a16` `#a8261b` | Iowan Old Style | vow |
| [Nongkrong Warung](https://juw12.github.io/themes/#nongkrong-warung) | `nongkrong-warung` | light + dark | `#f7f5f0` `#1f1e1c` `#a63d24` | DM Serif Display | nongkrong |
| [Mise Station](https://juw12.github.io/themes/#mise-station) | `mise-station` | light | `#f4efe6` `#1f2420` `#b4472b` | Iowan Old Style | mise |
| [Game Table Amber](https://juw12.github.io/themes/#game-table-amber) | `game-table-amber` | light + dark | `#fbf7f0` `#1c1917` `#b45309` | system-ui | game |
| [Teduh Field Guide](https://juw12.github.io/themes/#teduh-field-guide) | `teduh-field-guide` | light | `#f8f3e8` `#23302a` `#2f5d4a` | Fraunces | teduh |
| [Meetline Signal](https://juw12.github.io/themes/#meetline-signal) | `meetline-signal` | dark | `#0e1114` `#e7eaee` `#f2b233` | Barlow Semi Condensed | meetline |
| [Retrace Teal](https://juw12.github.io/themes/#retrace-teal) | `retrace-teal` | light + dark | `#f5f6f8` `#15191f` `#0f6b63` | Segoe UI Variable Text | retrace |
| [Tally Navy](https://juw12.github.io/themes/#tally-navy) | `tally-navy` | light + dark | `#f6f5f2` `#141414` `#1f3b5c` | -apple-system | tally |
| [Atomize Violet](https://juw12.github.io/themes/#atomize-violet) | `atomize-violet` | light | `#f8f7fb` `#1d1a24` `#6d28d9` | system-ui | atomize |
| [Undanu Rose Clay](https://juw12.github.io/themes/#undanu-rose-clay) | `undanu-rose-clay` | light | `#f8f5f2` `#26222b` `#b5826e` | Cormorant Garamond | undanu |
| [Peakwise Summit](https://juw12.github.io/themes/#peakwise-summit) | `peakwise-summit` | dark | `#0f1720` `#e8eef3` `#2ee6a0` | Inter | peakwise |
| [Handoff Lamp](https://juw12.github.io/themes/#handoff-lamp) | `handoff-lamp` | dark | `#0f0e0d` `#e8e6e3` `#e8a838` | ui-serif | handoff |
| [Shiphub Signal Red](https://juw12.github.io/themes/#shiphub-signal-red) | `shiphub-signal-red` | light + dark | `#fafaf9` `#1c1917` `#e5484d` | Inter | shiphub |
| [Spry Green](https://juw12.github.io/themes/#spry-green) | `spry-green` | light | `#ffffff` `#1f2330` `#1a7f5a` | Instrument Sans | spry |
| [The Morning Paper](https://juw12.github.io/themes/#the-morning-paper) | `the-morning-paper` | light | `#faf8f3` `#1a1a1a` `#8b1a1a` | Georgia | skills |
| [Studio Graphite](https://juw12.github.io/themes/#studio-graphite) | `studio-graphite` | dark | `#121314` `#ecedee` `#2563eb` | Segoe UI Semibold | skills |

## Rebuild

```
python tools/build.py     # src/merged.json + src/curation.json -> themes/, themes.json
python tools/site.py      # index.html, README.md, TEMPLATES.md
python tools/check.py     # gates
```

`tools/scan.py`, `tools/extract.py`, `tools/probe_live.py` and `tools/reconcile.py` are the scripts that read the
projects in the first place (they need the GitHub CLI and Playwright).

## Licence

MIT for the tokens and the code. Fonts named in a theme belong to their makers; check each font's licence.
