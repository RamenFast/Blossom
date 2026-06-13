# Blossom

A cohesive desktop theme: **AMOLED true-black**, soft **pink** and **gold**, with
a light blue for text — built so the *look itself* carries information
importance.

> **Status:** palette + plan locked 2026-06-13; theme files start next session.
> Lives in `~/.themes/Blossom/` so Cinnamon loads it directly; symlinked into
> `~/Dev/ClaudeWorkspace/blossom` for visibility.

## Palette

| | Colour | Role |
| --- | --- | --- |
| ⚫ | absolute black `#000000` | base (AMOLED) |
| 🌸 | pink ×2 (bright / dim) | **primary** accent — focus, selection, links; bright = important, dim = secondary |
| 🟡 | gold ×2 (bright / dim) | secondary / supporting ("yellow holds in pink") |
| 🩵 | `#eaf6ff` | text & icons — the Phosphor vectorscope icon's light blue |
| 🔴 | red | critical / error dialogues only |

The two-shade pairs double as hover/active states **and** the
information-importance tiering. Greys for borders / disabled / dividers are
derived from these via opacity — no extra named colours.

## Plan

A Cinnamon "look" is several parts, themed together:

- **GTK 3 / 4** — application widgets
- **Cinnamon** (`cinnamon/cinnamon.css`) — panel, menu, applets
- **Metacity / WM** — window borders
- **icons** + the accent colour

Approach: derive from `Mint-Y-Dark` (already dark), push backgrounds to true
black, recolour accents to the Blossom palette, and tune contrast so importance
reads through colour. Edit here → reload Cinnamon (`Ctrl+Alt+Esc`) to preview.

## Environment

Linux Mint · Cinnamon 6.6.7 · X11 · 40px panel. Currently: `Mint-Y-Dark-Aqua`
(Cinnamon + GTK), `Mint-Y-Sand` icons, `Mint-Y` WM.

## Open questions

- Which surface to start with — panel? GTK apps? terminal? the Hermes UI?
- The exact pink and gold hex values (two shades each)
- Build fresh vs. fork-and-recolour `Mint-Y-Dark`
