# LLMreadme — arxstories

Notes for any LLM working in this repo.

- Collections: `dispatches/` (ΛRX Intercept, current news) and `atlas/` (ΛRX Atlas, history). Same files per entry; Atlas folders are named `<year>-slug` (e.g. `509bc-...`) and carry `kind: atlas`, `year`, `pair`, `witnesses`.
- One dispatch = one folder in `dispatches/`, named `YYYY-MM-DD-short-slug`, containing `index.md`, `card.png`, `source.jpg` and `spec.json`. The `slug` in front matter must match the folder name.
- Never hand-edit `data/dispatches.json` or `data/atlas.json`. Run `python3 tools/build_index.py` after any change to a dispatch; it validates required fields and fails loudly.
- Every entry has `art: art.jpg` in its front matter: the clean image with no card text. Pages lead with the art; clicking it opens `card.png`, which stays the share image. For user-supplied cards with painted-in text, crop the cleanest text-free region into `art.png`.
- Re-render a card with `python3 tools/render.py <folder>/spec.json <folder>/card.png`. `spec.json` paths are relative to the spec file.
- The article body opens with the `**ΛRX INTERCEPT** · Dispatch · <date> · <city>` line, then the H1, the italic dek and the card image, and ends with `## Sources` grouped as Original reporting / Context / Framing, followed by the desk sign-off line.
- Editorial rule: only checkable facts in the desk's own voice; every argument is credited, in active voice, to a named actor, with the same verb for both sides. Run the flip test before committing. Intercept entries also carry The Stakes (public language vs. the concrete power stake beneath it), symmetric across sides; the article's last paragraph before Sources gives it. Never name the school or thinker behind this lens.
- Atlas articles open with `**ΛRX ATLAS** · Entry · <date> · <place>`, run 450–700 words in a Herodotean narrative voice (tellers named, legend marked, a passage weighing the evidence, a closing long view), and end with Sources grouped as Ancient witnesses / Modern scholarship and the `*Entered in the ΛRX Atlas · arxcortex.io*` line.
- Third collection: `currents/` (ΛRX Currents, trends in thought and the ideas behind them). Folders are named `YYYY-MM-DD-short-slug` like dispatches, carry `kind: currents`, `desk: ΛRX Currents`, the same files (`index.md`, `card.png`, `art.png`, `spec.json`), and publish at `https://arxcortex.github.io/arxstories/currents/<slug>/`. The body opens with `**ΛRX CURRENTS** · Current · <date> · <place>`, uses the H1 / italic dek / card / body / `## Sources` (Original reporting / Context / Framing) order, and ends with `*Entered in ΛRX Currents · arxcortex.io*`. Cards use `desk: "ΛRX CURRENTS"`; render with `python3 tools/render_card.py`.
- Optional front matter on any entry: `series: [atlas, currents]` lists every desk a story belongs to (a double byline shows as a "Series" line on the page); `memeplex:` with `ideas: [idea_id, ...]` and optional `current: <id>` links the story to the Memeplex (ids from arx-memeplex `ideas.json`; shown before Sources). `build_index.py` validates both.
- Commit message format: `Dispatch: <title>`, `Atlas: <title>` or `Currents: <title>`. Don't commit `tools/fonts/`.
- GitHub Pages publishes the story pages. `tools/build_site.py` writes them into `_site/` from the manifests and the article folders. Don't hand-write that HTML, and don't hand-edit the manifests. The site fetches `data/dispatches.json`, `data/atlas.json` and `data/currents.json` from Pages. It does not store the stories.

## Image sizes
- `art.jpg` and `source.jpg`: JPEG, quality 82, progressive, at most 2000px wide. Do not commit `art.png` or `source.png` for new stories.
- `card.png`: render at 3200×1800 with `tools/render.py`, then shrink in place to 1600×900 and quantize to 256 colors with optimize (keep the `card.png` name). Target under ~600 KB.
