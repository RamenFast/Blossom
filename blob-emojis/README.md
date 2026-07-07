# blob-emojis — Blobmoji across the desktop 🌸

Google's blob emoji — the squishy gumdrops of the Android KitKat→Nougat era
(the Lollipop look) — continued by the community as
[Blobmoji](https://github.com/C1710/blobmoji) (Noto Emoji fork, new emoji still
drawn blob-style), wired up as the emoji font for the whole desktop. Text fonts
are untouched: fontconfig only reroutes emoji glyph fallback.

## What's here

| file | what |
|---|---|
| `Blobmoji.ttf` | v15.0 release build (Unicode 15.0) — the font that gets installed |
| `75-blobmoji.conf` | the fontconfig rules (canonical copy) |
| `install.sh` | idempotent installer — user level + every flatpak; `--system`, `--uninstall` |
| `blobmoji/` | shallow clone of upstream (art sources; **gitignored**, not needed at runtime) |
| `docs/` | before/after receipts |

## How it works

1. The generic `emoji` family prefers **Blobmoji**. User config is processed before
   the system `60-generic.conf`, so Blobmoji outranks Noto Color Emoji without
   uninstalling it.
2. Explicit requests for other emoji fonts (Noto Color Emoji, Segoe UI Emoji,
   Twemoji, JoyPixels…) are rewritten to Blobmoji.
3. Every font lookup gets a weak `emoji` family appended — that routes emoji
   fallback in kitty/ghostty (charset queries), GTK/Qt (pango), and
   Chromium/Electron through Blobmoji for any base font, while never overriding
   glyphs the text font actually has (digits, symbols, letters stay put).

Noto Color Emoji stays installed as a safety net: emoji newer than Unicode 15.0
(post-2022 additions) render in Noto style instead of tofu boxes.

## Flatpaks (Emote, GIMP, OBS, …)

Flatpak sandboxes never read `~/.config/fontconfig` — each app has its own
`XDG_CONFIG_HOME` at `~/.var/app/<id>/config`. `install.sh` therefore drops the
conf into every installed flatpak's `config/fontconfig/conf.d/`; the font itself
reaches sandboxes automatically (host user fonts are mounted at
`/run/host/user-fonts`).

**Installed a new flatpak? Re-run `./install.sh`** so it gets the conf too.

## Applying / verifying / removing

- New app launches pick blobs up immediately; already-running apps keep their old
  emoji until restarted. Cinnamon shell itself: `Ctrl+Alt+Esc` restarts it in
  place (X11, windows survive).
- Verify host: `fc-match emoji` and `fc-match 'sans-serif:lang=und-zsye'` → `Blobmoji`.
- Verify a flatpak: `flatpak run --command=fc-match <app-id> emoji` → `Blobmoji`.
- Remove: `./install.sh --uninstall` (add `--system` if you installed with it).

## Caveats

- **Firefox** ignores fontconfig for emoji (ships its own Twemoji Mozilla):
  `about:config` → `font.name-list.emoji` → `Blobmoji`.
- Apps that draw emoji as **images** (Discord/Slack chat bodies, Twemoji-based
  websites) aren't using fonts and can't be themed this way.
- Blobmoji's own build tooling lives in `blobmoji/` if we ever want to rebuild
  the ttf from source (needs their noto-emoji build chain; the release ttf is fine).

Upstream: <https://github.com/C1710/blobmoji> · Apache-2.0 (art: CC-BY 4.0 per upstream README)
