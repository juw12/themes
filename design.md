# Design: the specimen book (index.html)

Who it is for: me, starting a new app and wanting a look I have already shipped; and anyone browsing for a
reference palette with its sources shown.

## Direction

A printer's specimen book. The page is plain paper and thin rules; the themes are the only decoration.
Each card is set entirely in its own theme (ground, panel, ink, accent, faces, corner radius), so the grid is
the picture. No illustration, no hero image, no icons.

## Signature

**Wear it.** The primary button on a card re-dresses the whole page in that theme, fonts included. The buttons
on a card are the specimen: the primary is the accent with its accent-ink, the quiet one is the surface with
the line colour, the JSON link is the accent as text.

## Rules

- The chrome wears Cairn Paper until a theme is worn. It uses the same eleven tokens the library exports.
- One accent per theme. On the chrome it appears in the headline's one italic word and in focus rings.
- Headline in the display face at 40 to 104px. Text 16px. Labels are 10 to 12px uppercase with tracking.
  Hex values, commands and counts are in the mono face.
- Rules are 1px `--line`. No shadows, gradients, glow or glass. Corners come from the theme's `--radius`.
- Numbers on the page are counted from the data at build time. Nothing is typed in by hand.
- Copy is plain: say what the thing is, then how to use it. No hype words, no emoji.
- A contrast number under 4.5:1 is shown with its meaning ("large only", "low"), not hidden.
- Works from 320px to 1440px. Touch targets are 36px or taller; the main ones 40px or taller.
