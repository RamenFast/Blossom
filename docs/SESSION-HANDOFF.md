# Blossom — session handoff

Ben reports **Blossom Control (`tools/blossom-control.py`) is "very buggy."** No
specific repro yet — this doc captures the architecture and the spots most likely
to be the cause, so the next session can debug efficiently. **Add concrete repro
steps under "Ben's bug notes" as you hit them** (what you clicked → what went
wrong).

## What it is

A tabbed GTK3 window (`Gtk.Notebook`): **Look · Taskbar · Logos · Icons**. It's a
plain `Gtk.Window` (not a `Gtk.Application`). Launched by `main()`; spawns
lower-left. Most actions shell out to gsettings / the other `tools/` scripts and
then tell Cinnamon to reload.

## How "apply" works (the fragile part)

Cinnamon caches aggressively, so every change needs a reload. The app uses dbus:

| Action | Mechanism | Reload | Risk |
|---|---|---|---|
| Apply/Revert look | `gsettings set …` | (instant) | low |
| Font | `gsettings font-name` | (instant) | **was buggy — see below** |
| Taskbar accent | rewrite `BLOSSOM-ACCENT` block in `cinnamon/cinnamon.css` | `org.Cinnamon.ReloadTheme` | medium |
| Panel glow | write `~/.local/share/blossom/glow.json` → run `tools/blossom-glow.py` → PNG | `ReloadTheme` | medium |
| Menu logo / bloom mark | copy `gallery/{logos,flowers}/<x>.svg` over `blossom-logo.svg`/`blossom-flower.svg` | `refresh_icons()` | **high** |
| Bloom button on/off | edit panel-launchers `*.json` `launcherList` | `ReloadXlet panel-launchers` | **high** |
| Icon rotation | `tools/blossom-rotate.py` | (instant) | low |

### Likely bug sources (in priority order)

1. **`refresh_icons()` toggles the icon theme and back** to bust St's in-process
   icon cache. *Confirmed this session:* `ReloadXlet menu@cinnamon.org` alone does
   **not** refresh a swapped logo — only a real icon-theme change does. Improved to
   flash through an installed theme (`Mint-Y-Sand` → … → `hicolor` fallback) so the
   blink shows real icons, not blank ones; still a brief flash, and a mid-toggle
   kill could leave the desktop on the temp theme. A cleaner approach would avoid
   the global toggle (e.g. alternate the menu-icon name).
2. **Bloom on/off edits the panel-launchers JSON while the applet is running.**
   External edits can race with the applet's own saves (it may overwrite, or not
   pick the change up until `ReloadXlet`). Reproduce by toggling rapidly.
3. **Combos fire `changed` during `refresh()`.** Guarded by `self._loading`, which
   is the single point of failure. The font combo had this bug (silently changed
   Ben's font to Inter on populate). Fixed this session — `on_font`, `on_accent`,
   and `on_pick_pack` now ALSO bail if the new value equals the current one, so a
   spurious `changed` is a no-op regardless of the `_loading` guard. (Other
   handlers — focus/auto/bloom checkbuttons, glow — are click-only, lower risk.)
4. **State goes stale** if anything is changed outside the app (system settings,
   another launch). There's no file/gsettings watching; `refresh()` only runs on
   open and after the app's own actions.
5. **Accent live render** was historically hard to confirm (screenshots miss it
   because `gnome-screenshot` steals focus, so no taskbar item is `:active`). The
   image-based accents (arches, 80% L) were **removed** at Ben's request; only the
   border-based ones remain (Bottom / Top / full-L), which are crisp + reliable.

## Known-fixed this session
- Font picker no longer changes the font on load (guarded). Restored Ubuntu 10.
- `on_accent` + `on_pick_pack` given the same "only act on a real change" guard.
- Accent assets for arches/80%-L removed; `ACCENTS` is now 3 border styles
  (Bottom / Top / full-L).
- `refresh_icons()` flashes through a real installed theme instead of blank hicolor.

## v1.0.0 era (2026-07-07)
- Released on GitHub as **v1.0.0** — deb + rpm + source tarball + SHA256SUMS,
  built by `packaging/build-packages.sh` (keep its `VERSION` == the tag).
- **Window position memory added**: `configure-event` tracks, close saves to
  `~/.local/share/blossom/control-window.json`, launch restores (validated
  against current monitors; lower-left fallback). Verified on Xvfb+openbox:
  exact round-trip, off-screen state falls back cleanly.
- Panel setup (menu logo + launcher) extracted from the README into
  `tools/panel-setup.sh` (idempotent, verified against Ben's live config).

## Window identity / "why does it behave differently than other buttons"
- The **bloom button is a `panel-launchers@cinnamon.org` launcher** — a *static
  shortcut*. Panel-launchers **never show a running indicator**; that's a
  different applet from the **grouped-window-list** (where the other app buttons
  live, which do show running state). So the flower launcher inherently behaves
  differently from the taskbar app buttons.
- When Blossom Control runs, its *window* appears in the grouped-window-list (far
  right, since it's unpinned). Ben unpinned it (respected — we don't re-pin).
- Options if Ben wants it to behave like the others: (a) pin
  `blossom-control.desktop` in the grouped-window-list AND drop the panel-launcher
  (one icon = launcher + indicator), or (b) make blossom-control a real
  `Gtk.Application` (cleaner window↔app association) — not done yet (risky refactor
  while the app is already buggy).

## Files
- `tools/blossom-control.py` — the GUI.
- `tools/blossom-glow.py` — panel glow PNG generator (reads glow.json).
- `tools/blossom_icons.py` — icon/logo/flower/gallery generators.
- `tools/blossom-rotate.py` — icon-pack rotation.
- `gallery/{logos,flowers}/*.svg` — variants for the Logos tab.
- `cinnamon/cinnamon.css` — has managed blocks: `BLOSSOM-ACCENT`, `BLOSSOM-PANEL-GLOW`.

## Next-session checklist
- [ ] **Get concrete repro steps from Ben** (see below) — top priority.
- [ ] Replace the icon-theme toggle with a fully non-flashy refresh (alternate the
      `menu-icon` name?). *Partly done:* flashes through a real theme now.
- [x] Audit combo `changed` handlers for the load-time re-apply bug (font/accent/pack).
- [ ] Consider `Gtk.Application` + a single window-list pin to unify the bloom button.
- [ ] Add light state-watching so the UI doesn't go stale.

## Ben's bug notes
<!-- Ben: drop specific repros here — "clicked X on tab Y, expected Z, got W" -->
-
