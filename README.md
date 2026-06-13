# Blossom

A cohesive Cinnamon desktop theme: **AMOLED true-black**, soft **pink** (primary)
and **gold** (secondary), with a light blue for text — built so the *look itself*
carries information importance.

![Blossom across the desktop](docs/hero.png)

## Palette

| | Colour | Role |
| --- | --- | --- |
| ⚫ | `#000000` | base — true black (AMOLED); raised surfaces lift to `#0a0a0a`–`#3b3b3b` |
| 🌸 | pink `#db3776` | **primary** accent — selection, focus, links, sliders, the suggested/primary action, the active window, menu selection |
| 🟡 | gold `#f1bf40` | **secondary / supporting** — marks *today* in the calendar (the reference point) and all *warnings* |
| 🩵 | `#eaf6ff` | text & icons — the Phosphor vectorscope's light blue (dims toward `#9fb3c2` for secondary text) |
| 🔴 | red `#ec4e53` | critical only — close button, log-out/shutdown, "remove", destructive actions, demands-attention |
| 🟢 | green `#52a462` | kept (softened) purely for the *success* semantic |

The design rule: **pink is what you're acting on, gold is the reference you're
acting against, red is danger.** Importance reads through colour — the bright
accent lands on the one element that matters right now, everything else stays
black-and-light-blue and recedes.

## What's themed

A full Cinnamon "look", all driven from one palette:

- **Cinnamon shell** (`cinnamon/`) — panel, menu, calendar, applets, popups, OSD
- **GTK 3** (`gtk-3.0/`) — application widgets + recoloured check/radio/switch assets
- **GTK 4 / libadwaita** (`gtk-4.0/`, `libadwaita-1.5/`, `libadwaita-1.7/`) — incl. a forced pink accent
- **Metacity** (`metacity-1/`) — window borders / title bars (true-black, light-blue title, red close)
- **GTK 2** (`gtk-2.0/`) — legacy apps
- **xfwm4 / openbox-3** — carried through for completeness

## How it's built

Rather than hand-edit ~1.5 MB of upstream CSS, the theme is **generated** by a
small HSL colour engine, `tools/blossomize.py`, which forks Linux Mint's
`Mint-Y-Dark-Aqua` (+ `Mint-L-Dark-Aqua` window borders) and routes every colour:

- near-neutral **darks** → a black-anchored ramp (true-black base, gentle elevation)
- near-neutral **lights** → tints of `#eaf6ff` (text / icons)
- saturated **blue** (Mint's accent family) → **pink**
- saturated **orange** → **gold**;  **red** kept (cleaned);  **green** kept (softened, success only)

It also reconciles a few semantics the hue-router can't infer: the *suggested
action* (green upstream) is pulled onto the pink accent ramp, libadwaita's accent
is forced pink, and a small "Blossom polish" block paints menu/calendar selection.

```bash
python3 tools/blossomize.py     # regenerates every theme subdir in place
```

The generated files are committed, so the theme is usable without running the
engine — re-run it only to **re-tune the palette**. The knobs live at the top of
`blossomize.py` (`PINK_HUE`, `PINK_SAT_MUL`, `PINK_L_LIFT`, `GOLD_HUE`, the dark
ramp `DARK_KNEE`/`DARK_SLOPE`, …). Want a softer, more pastel pink? Nudge
`PINK_L_LIFT` up and `PINK_SAT_MUL` down, then re-run.

## Install & apply

Lives in `~/.themes/Blossom/` so Cinnamon loads it directly. Apply with:

```bash
gsettings set org.cinnamon.theme name 'Blossom'                    # shell
gsettings set org.cinnamon.desktop.interface gtk-theme 'Blossom'   # apps
gsettings set org.cinnamon.desktop.wm.preferences theme 'Blossom'  # window borders
```

…or pick **Blossom** in *System Settings → Themes*. Pairs well with the
**Mint-Y-Sand** icon set (gold-leaning folders echo the secondary accent).
Iterate live: edit → re-run the engine → re-select the theme (or `Ctrl+Alt+Esc`
to reload Cinnamon).

## Environment

Built and tested on Linux Mint · Cinnamon 6.6.7 · X11 · 40 px panel.
