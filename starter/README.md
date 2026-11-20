# starter

One screen (top bar, table, form, totals) that uses only the theme tokens.

1. Copy this folder into the new project.
2. `python theme.py pull <id> --to starter/theme.css` (ids: `python theme.py list`).
3. Build on `app.css`. It never names a colour or a font, only `var(--...)` tokens.

Try any theme without copying anything: open `index.html?theme=<id>` while the folder is still inside the library,
or use the picker in the top bar. Outside the library the picker hides itself and `theme.css` is used.

If the theme names web fonts (see `Web fonts:` in the comment at the top of `theme.css`), add that URL as a
`<link rel="stylesheet">` in `index.html`. The sample rows are made up.
