#!/usr/bin/env python3
"""
blossomize.py — generate the Blossom desktop theme.

Blossom is AMOLED true-black with a soft pink primary accent, gold secondary,
and #eaf6ff (light-blue) text. Rather than hand-edit ~1.5 MB of Mint-Y CSS, we
treat colour transformation as a principled HSL routing problem:

  * near-neutral darks  -> a black-anchored grey ramp (AMOLED elevation)
  * near-neutral lights -> tints of #eaf6ff (text / icons)
  * saturated BLUE      -> PINK   (the Mint accent family becomes our primary)
  * saturated ORANGE    -> GOLD   (warnings + secondary accent)
  * saturated RED        kept as a clean error red
  * saturated GREEN      kept (softened) for success semantics

The same per-colour function drives CSS, SVG, XML, GTK-2 rc files and the
accent-bearing PNG assets, so every surface stays consistent. Re-runnable:
it regenerates the theme tree from the system Mint sources each time, leaving
README.md / tools/ / .git untouched.
"""

import colorsys
import re
import shutil
from pathlib import Path

# ----------------------------------------------------------------------------
# Sources & output
# ----------------------------------------------------------------------------
THEMES = Path("/usr/share/themes")
SRC = THEMES / "Mint-Y-Dark-Aqua"          # body: cinnamon, gtk-*, libadwaita…
SRC_METACITY = THEMES / "Mint-L-Dark-Aqua" / "metacity-1"   # window borders
OUT = Path(__file__).resolve().parent.parent                # repo root = theme root

# Subtrees copied verbatim from SRC, then transformed in place.
BODY_DIRS = [
    "cinnamon", "gtk-2.0", "gtk-3.0", "gtk-4.0",
    "libadwaita-1.5", "libadwaita-1.7", "xfwm4", "openbox-3",
]

# ----------------------------------------------------------------------------
# Palette knobs (tune these between iterations)
# ----------------------------------------------------------------------------
TEXT = (0xEA, 0xF6, 0xFF)        # #eaf6ff — primary text / icon light-blue

# Dark neutral ramp: lightness L in [0,1] -> black-anchored grey lightness.
# main window bg (#202023, L~0.13) lands on pure black; surfaces lift gently.
DARK_KNEE = 0.135
DARK_SLOPE = 1.85

# Light neutral tint: greys with L above this become tints of TEXT.
LIGHT_THRESHOLD = 0.52

# Saturated-colour routing (hue in degrees) and the look of each family.
PINK_HUE = 337.0                 # primary accent
PINK_SAT_MUL = 0.92
PINK_L_LIFT = 0.04               # nudge mids toward a softer, brighter pink

GOLD_HUE = 43.0                  # secondary accent / warnings
GOLD_SAT_MUL = 0.98
GOLD_L_LIFT = 0.02

RED_HUE = 358.0                  # critical / error only
RED_SAT_MUL = 0.95

GREEN_HUE = 132.0                # success semantics (kept, softened)
GREEN_SAT_MUL = 0.72

# Classification thresholds
NEUTRAL_SAT = 0.12               # below this = neutral grey
DARK_MUTED_L = 0.30              # dark + low-ish sat = treat as neutral surface
DARK_MUTED_SAT = 0.42

# ----------------------------------------------------------------------------
# Colour transform (cached)
# ----------------------------------------------------------------------------
_cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _hls_to_rgb(h_deg: float, l: float, s: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb((h_deg % 360) / 360.0, _clamp01(l), _clamp01(s))
    return round(r * 255), round(g * 255), round(b * 255)


def _neutral(l: float) -> tuple[int, int, int]:
    if l > LIGHT_THRESHOLD:
        # tint of #eaf6ff, dimmed proportionally to the source lightness
        f = min(1.0, l / 0.965)
        return tuple(round(c * f) for c in TEXT)
    # black-anchored dark ramp, pure neutral grey
    nl = _clamp01((l - DARK_KNEE) * DARK_SLOPE)
    v = round(nl * 255)
    return (v, v, v)


def transform(r: int, g: int, b: int) -> tuple[int, int, int]:
    key = (r, g, b)
    hit = _cache.get(key)
    if hit is not None:
        return hit

    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hd = h * 360.0

    if s < NEUTRAL_SAT or (l < DARK_MUTED_L and s < DARK_MUTED_SAT):
        out = _neutral(l)
    elif RED_HUE_LO <= hd or hd < RED_HUE_HI:          # reds (wraps 0)
        out = _hls_to_rgb(RED_HUE, l, s * RED_SAT_MUL)
    elif hd < GOLD_HUE_HI:                              # orange / yellow -> gold
        out = _hls_to_rgb(GOLD_HUE, l + GOLD_L_LIFT, s * GOLD_SAT_MUL)
    elif hd < GREEN_HUE_HI:                             # green -> success green
        out = _hls_to_rgb(GREEN_HUE, l, s * GREEN_SAT_MUL)
    else:                                               # cyan/blue/purple -> pink
        out = _hls_to_rgb(PINK_HUE, l + PINK_L_LIFT, s * PINK_SAT_MUL)

    _cache[key] = out
    return out


# hue band edges (degrees)
RED_HUE_LO = 345.0
RED_HUE_HI = 15.0
GOLD_HUE_HI = 70.0
GREEN_HUE_HI = 170.0


# ----------------------------------------------------------------------------
# Text transformation
# ----------------------------------------------------------------------------
def _hx(n: int) -> str:
    return f"{n:02x}"


def _sub_hex(m: re.Match) -> str:
    hexpart = m.group(1)
    if len(hexpart) == 3:
        r, g, b = (int(c * 2, 16) for c in hexpart)
        nr, ng, nb = transform(r, g, b)
        return "#" + _hx(nr) + _hx(ng) + _hx(nb)
    r, g, b = int(hexpart[0:2], 16), int(hexpart[2:4], 16), int(hexpart[4:6], 16)
    nr, ng, nb = transform(r, g, b)
    tail = hexpart[6:8]  # preserve 8-digit alpha
    return "#" + _hx(nr) + _hx(ng) + _hx(nb) + tail


def _sub_hex_delim(m: re.Match) -> str:
    return m.group(1) + _sub_hex(m)


def _sub_rgb(m: re.Match) -> str:
    fn, r, g, b, alpha = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    nr, ng, nb = transform(int(r), int(g), int(b))
    return f"{fn}({nr}, {ng}, {nb}{alpha or ''})"


# 6/8-digit hex in a CSS value position, guarded against id-selectors.
RE_CSS_HEX = re.compile(r"(?<![\w&#-])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6})(?![0-9a-fA-F\w-])")
# 3-digit hex only after a value delimiter (catches `#fff`, skips `#abc-foo`).
RE_CSS_HEX3 = re.compile(r"(?<=[:,(\s])#([0-9a-fA-F]{3})(?![0-9a-fA-F\w-])")
# Permissive hex for non-CSS text (svg/xml/rc) — no id-selector ambiguity there.
RE_HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
# rgb()/rgba() with integer channels
RE_RGB = re.compile(
    r"(rgba?)\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(,\s*[0-9.]+\s*)?\)"
)


def transform_css(text: str) -> str:
    text = RE_CSS_HEX.sub(lambda m: _sub_hex(m), text)
    text = RE_CSS_HEX3.sub(lambda m: _sub_hex(m), text)
    text = RE_RGB.sub(_sub_rgb, text)
    return text


# ----------------------------------------------------------------------------
# Accent reconciliation
#
# Mint colours the "suggested action" (primary) button GREEN, separate from the
# blue selection accent. Blossom's thesis is "pink = primary", so we recolour
# suggested-action to the accent — but ONLY inside suggested-action rules, so the
# *success* semantic stays green. We do it by swapping the suggested-action
# greens for the blue-accent shades *before* the hue router runs, so they land on
# the exact same pink ramp as the rest of the accent.
# ----------------------------------------------------------------------------
SUGGESTED_GREEN_TO_BLUE = {
    "#6db442": "#1f9ede",   # normal  -> accent
    "#88c663": "#5cb9e8",   # hover   -> lighter accent
    "#568f34": "#197eb1",   # active  -> darker accent
}
RE_RULE = re.compile(r"([^{}]*?)\{([^{}]*)\}", re.S)


def pre_accent(text: str) -> str:
    def repl(m: re.Match) -> str:
        sel, body = m.group(1), m.group(2)
        if "suggested-action" in sel:
            for green, blue in SUGGESTED_GREEN_TO_BLUE.items():
                body = re.sub(green, blue, body, flags=re.I)
        return sel + "{" + body + "}"

    return RE_RULE.sub(repl, text)


# Pink accent for libadwaita / GTK4 named colours (post-transform append).
_PINK_BG = "#%02x%02x%02x" % transform(0x1F, 0x9E, 0xDE)   # == accent -> pink
_GOLD = "#%02x%02x%02x" % transform(0xF2, 0x78, 0x35)      # == warning -> gold
ACCENT_OVERRIDE = f"""
/* Blossom: primary accent = pink */
@define-color accent_bg_color {_PINK_BG};
@define-color accent_fg_color #eaf6ff;
@define-color accent_color #ff93c0;
"""

# Cinnamon shell polish: pink marks the active / about-to-act item, matching how
# selection reads in GTK lists. Appended so it wins over the base grey rules.
CINNAMON_OVERRIDE = f"""
/* ===== Blossom polish — pink marks the active element ===== */
.menu-application-button-selected,
.menu-category-button-selected,
.menu-category-button:hover,
.appmenu-application-button-selected,
.appmenu-category-button-selected,
.appmenu-category-button:hover {{
  background-color: {_PINK_BG};
  color: #eaf6ff;
  border-radius: 6px; }}

.popup-menu-item:active {{
  background-color: {_PINK_BG};
  color: #eaf6ff; }}

/* Gold is the supporting accent: it always marks "today" — the reference point —
   while pink marks what you're acting on (hover / a different selected day). */
.calendar-today,
.calendar-today:selected {{
  font-weight: bold;
  color: {_GOLD};
  background-color: rgba(242, 191, 64, 0.16);
  border: 1px solid rgba(242, 191, 64, 0.7);
  border-radius: 6px; }}
.calendar-today:hover {{
  color: #eaf6ff;
  background-color: {_PINK_BG};
  border-color: {_PINK_BG}; }}
.calendar-not-today:selected {{
  font-weight: bold;
  color: #eaf6ff;
  background-color: {_PINK_BG};
  border-radius: 6px; }}
"""


def transform_markup(text: str) -> str:
    text = RE_HEX.sub(lambda m: _sub_hex(m), text)
    text = RE_RGB.sub(_sub_rgb, text)
    return text


# ----------------------------------------------------------------------------
# PNG transformation (accent assets)
# ----------------------------------------------------------------------------
def transform_png(path: Path) -> None:
    from PIL import Image

    img = Image.open(path).convert("RGBA")
    colors = img.getcolors(maxcolors=1 << 24)
    if colors is None:
        return
    lut: dict[tuple[int, int, int, int], tuple[int, int, int, int]] = {}
    for _count, px in colors:
        r, g, b, a = px
        if a == 0:
            lut[px] = px
        else:
            nr, ng, nb = transform(r, g, b)
            lut[px] = (nr, ng, nb, a)
    img.putdata([lut[px] for px in img.getdata()])
    img.save(path)


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
CSS_EXT = {".css"}
MARKUP_EXT = {".svg", ".xml", ".rc", ".theme", ".themerc", ".gtkrc"}
MARKUP_NAMES = {"themerc", "gtkrc", "apps.rc", "main.rc"}


def is_markup(p: Path) -> bool:
    return p.suffix.lower() in MARKUP_EXT or p.name in MARKUP_NAMES


def process_file(p: Path) -> None:
    if p.suffix.lower() == ".png":
        try:
            transform_png(p)
        except Exception as e:  # noqa: BLE001
            print(f"  ! png skip {p.name}: {e}")
        return
    if p.suffix.lower() in CSS_EXT:
        data = p.read_text(encoding="utf-8", errors="surrogateescape")
        p.write_text(transform_css(data), encoding="utf-8", errors="surrogateescape")
    elif is_markup(p):
        data = p.read_text(encoding="utf-8", errors="surrogateescape")
        p.write_text(transform_markup(data), encoding="utf-8", errors="surrogateescape")
    # else: leave other binaries (e.g. font caches) alone


INDEX_THEME = """[Desktop Entry]
Type=X-GNOME-Metatheme
Name=Blossom
Comment=AMOLED true-black with soft pink & gold — importance through colour
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme=Blossom
MetacityTheme=Blossom
IconTheme=Mint-Y-Sand
CursorTheme=Bibata-Modern-Classic
ButtonLayout=:minimize,maximize,close
"""


def main() -> None:
    print(f"Blossom: generating into {OUT}")

    # 1. (re)create theme subtrees from sources
    for d in BODY_DIRS:
        src = SRC / d
        dst = OUT / d
        if dst.exists():
            shutil.rmtree(dst)
        if src.exists():
            shutil.copytree(src, dst)
    # window borders
    mdst = OUT / "metacity-1"
    if mdst.exists():
        shutil.rmtree(mdst)
    shutil.copytree(SRC_METACITY, mdst)

    # 1b. reconcile suggested-action -> accent in GTK CSS (before hue routing)
    for rel in ["gtk-3.0/gtk.css", "gtk-3.0/gtk-dark.css",
                "gtk-4.0/gtk.css", "gtk-4.0/gtk-dark.css"]:
        f = OUT / rel
        if f.exists():
            f.write_text(pre_accent(f.read_text(encoding="utf-8", errors="surrogateescape")),
                         encoding="utf-8", errors="surrogateescape")

    # 2. transform every file
    n_text = n_png = 0
    for d in BODY_DIRS + ["metacity-1"]:
        root = OUT / d
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() == ".png":
                process_file(p)
                n_png += 1
            elif p.suffix.lower() in CSS_EXT or is_markup(p):
                process_file(p)
                n_text += 1

    # 2b. force the pink accent into libadwaita / GTK4 named colours
    for rel in ["libadwaita-1.5/base.css", "libadwaita-1.5/defaults-dark.css",
                "libadwaita-1.7/base.css", "libadwaita-1.7/defaults-dark.css",
                "gtk-4.0/gtk.css", "gtk-4.0/gtk-dark.css"]:
        f = OUT / rel
        if f.exists():
            with f.open("a", encoding="utf-8") as fh:
                fh.write(ACCENT_OVERRIDE)
    with (OUT / "cinnamon" / "cinnamon.css").open("a", encoding="utf-8") as fh:
        fh.write(CINNAMON_OVERRIDE)

    # 3. metacity/openbox theme name cosmetics + index.theme
    (OUT / "index.theme").write_text(INDEX_THEME, encoding="utf-8")
    for name_path in [
        OUT / "metacity-1" / "metacity-theme-2.xml",
        OUT / "metacity-1" / "metacity-theme-3.xml",
    ]:
        if name_path.exists():
            t = name_path.read_text(encoding="utf-8", errors="surrogateescape")
            t = t.replace("<name>Arc</name>", "<name>Blossom</name>")
            name_path.write_text(t, encoding="utf-8", errors="surrogateescape")

    print(f"  transformed {n_text} text files, {n_png} png files")
    print(f"  unique colours mapped: {len(_cache)}")
    print("done.")


if __name__ == "__main__":
    main()
