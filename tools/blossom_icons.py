#!/usr/bin/env python3
"""
blossom_icons.py — generate the Blossom icon theme.

A cohesive AMOLED/pink icon language to match the Blossom GTK/Cinnamon theme:
folders are a void-dark body under a pink (or gold) header, differentiated by a
light-blue (#eaf6ff) line glyph; trash / drives / computer / network are drawn in
the same dark-body + light-blue-line + pink-accent language.

Everything else (app icons, mimetypes, the long tail) is inherited from
Papirus-Dark, so the set is small, consistent, and high-impact where it shows:
the Nemo sidebar, the desktop, and file dialogs.

Output: a scalable SVG icon theme at  icons/Blossom/  (symlinked to ~/.icons/Blossom).
"""

from pathlib import Path
import shutil

OUT = Path(__file__).resolve().parent.parent / "icons" / "Blossom"

# ---- palette ---------------------------------------------------------------
PINK = "#db3776"
GOLD = "#f1bf40"
LB   = "#eaf6ff"   # light-blue line glyphs
BODY = "#16181d"   # folder body — the void, just visible on true black
EDGE = "#2a2e37"   # subtle defining edge
RED  = "#ec4e53"

# ---- folder template -------------------------------------------------------
# back panel (incl. tab) + front pocket + pocket highlight + defining edge.
# Corners are squared off (small radii) per Ben's preference for square > round,
# and the pocket carries a vertical light→dark gradient + a top highlight line so
# the folder reads with a layer of depth instead of looking flat.
_BACK = ("M7 10 h11 a1.4 1.4 0 0 1 1.2 0.8 l1.4 2.4 h18.6 a1.4 1.4 0 0 1 1.4 1.4 v20.8 "
         "a1.4 1.4 0 0 1 -1.4 1.4 H7 a1.4 1.4 0 0 1 -1.4 -1.4 V11.4 a1.4 1.4 0 0 1 1.4 -1.4 z")
_POCK = "M5 19 H43 V37.4 a1.4 1.4 0 0 1 -1.4 1.4 H6.4 a1.4 1.4 0 0 1 -1.4 -1.4 z"


def folder(glyph: str = "", top: str = PINK) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
        '<defs>'
        '<linearGradient id="fdepth" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1b1e25"/>'
        '<stop offset="1" stop-color="#0c0e12"/></linearGradient>'
        '</defs>'
        # back panel + a thin top gloss so the coloured header has dimension
        f'<path d="{_BACK}" fill="{top}"/>'
        f'<rect x="7" y="10" width="35" height="2.4" fill="#ffffff" opacity="0.16"/>'
        # front pocket with depth gradient
        f'<path d="{_POCK}" fill="url(#fdepth)"/>'
        f'<rect x="5" y="19" width="38" height="1.2" fill="{LB}" opacity="0.20"/>'
        f'<path d="{_POCK}" fill="none" stroke="{EDGE}" stroke-width="0.7"/>'
        f'{glyph}</svg>'
    )


def _g(paths: str, w: float = 1.7, fill: str = "none", op: float = 0.92) -> str:
    """A light-blue line glyph group sitting on the pocket."""
    return (f'<g fill="{fill}" stroke="{LB}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-linejoin="round" opacity="{op}">{paths}</g>')


# glyphs centred on the pocket (~x16-32, y23-38)
GLYPHS = {
    "documents": _g('<path d="M18 27h12"/><path d="M18 31h12"/><path d="M18 35h7"/>'),
    "download":  _g('<path d="M24 23v9"/><path d="M20 29l4 4 4-4"/><path d="M18 37h12"/>'),
    "music":     _g('<path d="M28 24v9"/><circle cx="25" cy="33.5" r="2.4" fill="%s" stroke="none"/>'
                    '<path d="M28 24q3 .6 3 2.6"/>' % LB),
    "pictures":  _g('<rect x="17" y="24" width="14" height="12" rx="1.5"/>'
                    '<circle cx="21.5" cy="28" r="1.4" fill="%s" stroke="none"/>'
                    '<path d="M18 35l4-4 3 2.5 3.5-4 2.5 3"/>' % LB),
    "videos":    _g('<path d="M21 25.5l8 4.8-8 4.8z" fill="%s" stroke="none"/>' % LB),
    "publicshare": _g('<circle cx="20" cy="27" r="2"/><circle cx="29" cy="26" r="2"/>'
                      '<circle cx="26" cy="35" r="2"/><path d="M21.8 27.7l5.4 6.4M22 27.2l6-.8"/>'),
    "templates": _g('<path d="M20 24l8 0 0 12-8 0z"/><path d="M20 28h8M24 24v12"/>', w=1.4),
    "recent":    _g('<circle cx="24" cy="30.5" r="5.2"/><path d="M24 27.5v3.3l2.2 1.4"/>'),
    "search":    _g('<circle cx="23" cy="29" r="4"/><path d="M26.2 32.2l3.3 3.3"/>'),
    "home":      _g('<path d="M18 30.5l6-5.5 6 5.5"/><path d="M20 30v6.5h8V30"/>'),
    "desktop":   _g('<rect x="17" y="24.5" width="14" height="9" rx="1"/>'
                    '<path d="M22 33.5l-1 3h6l-1-3M20 37h8"/>'),
    "drag":      _g('<path d="M24 24v8M20.5 28.5l3.5 3.5 3.5-3.5"/>'),
}

# ---- non-folder icons ------------------------------------------------------
def _svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">{body}</svg>'


def trash(full: bool = False) -> str:
    contents = PINK if full else LB
    lid_y = 13 if full else 14
    body = (
        # can body
        f'<path d="M15 18 h18 l-1.6 20.2 a2.2 2.2 0 0 1 -2.2 2 H18.8 a2.2 2.2 0 0 1 -2.2 -2 z" '
        f'fill="{BODY}" stroke="{EDGE}" stroke-width="0.7"/>'
        # ribs
        f'<g stroke="{contents}" stroke-width="1.7" stroke-linecap="round" opacity="0.92">'
        f'<path d="M21 23v12"/><path d="M24 23v12.5"/><path d="M27 23v12"/></g>'
        # lid + handle in pink
        f'<rect x="12" y="{lid_y}" width="24" height="3.2" rx="1.6" fill="{PINK}"/>'
        f'<path d="M20 {lid_y-3} h8 a1.5 1.5 0 0 1 1.5 1.5 V{lid_y} h-11 V{lid_y-1.5} '
        f'a1.5 1.5 0 0 1 1.5 -1.5 z" fill="{PINK}"/>'
    )
    return _svg(body)


def harddisk() -> str:
    return _svg(
        f'<rect x="9" y="18" width="30" height="13" rx="1.4" fill="{BODY}" stroke="{EDGE}" stroke-width="0.8"/>'
        f'<circle cx="32" cy="24.5" r="2.2" fill="none" stroke="{LB}" stroke-width="1.6" opacity="0.9"/>'
        f'<circle cx="32" cy="24.5" r="0.6" fill="{LB}"/>'
        f'<rect x="13" y="22.5" width="10" height="1.7" rx="0.85" fill="{LB}" opacity="0.8"/>'
        f'<rect x="13" y="26" width="7" height="1.7" rx="0.85" fill="{LB}" opacity="0.55"/>'
        f'<rect x="9.6" y="30" width="28.8" height="2.2" rx="1.1" fill="{PINK}"/>'
    )


def usb() -> str:
    return _svg(
        f'<rect x="20" y="22" width="8" height="16" rx="1.2" fill="{BODY}" stroke="{EDGE}" stroke-width="0.8"/>'
        f'<path d="M22 22v-3.5a2 2 0 0 1 4 0V22" fill="none" stroke="{LB}" stroke-width="1.6"/>'
        f'<rect x="22" y="26" width="4" height="2" fill="{PINK}"/>'
        f'<rect x="22" y="30" width="4" height="2" fill="{LB}" opacity="0.6"/>'
    )


def optical() -> str:
    return _svg(
        f'<circle cx="24" cy="24" r="13" fill="{BODY}" stroke="{EDGE}" stroke-width="0.8"/>'
        f'<circle cx="24" cy="24" r="12.5" fill="none" stroke="{PINK}" stroke-width="1.4" opacity="0.85"/>'
        f'<circle cx="24" cy="24" r="3.4" fill="none" stroke="{LB}" stroke-width="1.6"/>'
        f'<path d="M24 12.5a11.5 11.5 0 0 1 9 4.6" fill="none" stroke="{LB}" stroke-width="1.6" opacity="0.6"/>'
    )


def computer() -> str:
    return _svg(
        f'<rect x="11" y="14" width="26" height="17" rx="1.5" fill="{BODY}" stroke="{EDGE}" stroke-width="0.8"/>'
        f'<rect x="13.5" y="16.5" width="21" height="12" rx="1" fill="none" stroke="{PINK}" stroke-width="1.4" opacity="0.8"/>'
        f'<path d="M20 31l-1.2 4h10.4l-1.2-4M16 35h16" fill="none" stroke="{LB}" stroke-width="1.7" stroke-linecap="round"/>'
    )


def editor() -> str:
    """A text-editor mark for xed: a little scene — a brick house (front wall +
    chimney) on a green lawn with a tree, and a glowing text-input cursor (I-beam)
    in a lit window on the wall. The 'document' becomes the house wall facing you."""
    BRICK = "#c25a4f"   # warm brick red, readable on the void
    MORTAR = "#34251f"  # dark mortar between bricks
    ROOF = "#8f4a39"    # darker clay roof
    GRASS = "#3fbf63"   # lawn green
    GRASSH = "#5fe089"  # lawn highlight
    LEAF = "#37c46a"    # tree canopy
    TRUNK = "#7a5a36"   # tree trunk
    return _svg(
        # ---- lawn (wavy-topped green strip) ----
        f'<path d="M2 39 q7 -3 12 0 t12 0 t12 0 t10 0 V46 H2 Z" fill="{GRASS}"/>'
        f'<path d="M2 39 q7 -3 12 0 t12 0 t12 0 t10 0" fill="none" '
        f'stroke="{GRASSH}" stroke-width="1.1" opacity="0.8"/>'
        # ---- tree (left) ----
        f'<rect x="7.2" y="33" width="2.6" height="9" rx="1" fill="{TRUNK}"/>'
        f'<circle cx="8.5" cy="30" r="5.2" fill="{LEAF}"/>'
        f'<circle cx="5.4" cy="32" r="3.4" fill="{LEAF}"/>'
        f'<circle cx="11.6" cy="32" r="3.4" fill="{LEAF}"/>'
        f'<circle cx="7" cy="28.5" r="1.2" fill="{GRASSH}" opacity="0.7"/>'
        # ---- house: roof + chimney + brick wall ----
        f'<rect x="33" y="9" width="4.2" height="8" fill="{BRICK}" stroke="{MORTAR}" stroke-width="0.6"/>'
        f'<path d="M15 19 L28 10.5 L41 19 Z" fill="{ROOF}" stroke="{MORTAR}" stroke-width="0.7" stroke-linejoin="round"/>'
        f'<rect x="17" y="19" width="22" height="21" fill="{BRICK}" stroke="{MORTAR}" stroke-width="0.7"/>'
        # brick courses (mortar lines) + staggered head joints
        f'<g stroke="{MORTAR}" stroke-width="0.8">'
        f'<path d="M17 24.2h22M17 29.4h22M17 34.6h22"/>'
        f'<path d="M22 19v5.2M28 19v5.2M34 19v5.2"/>'
        f'<path d="M19.4 24.2v5.2M25 24.2v5.2M31 24.2v5.2M36.5 24.2v5.2"/>'
        f'<path d="M22 29.4v5.2M28 29.4v5.2M34 29.4v5.2"/>'
        f'<path d="M19.4 34.6v5.4M25 34.6v5.4M31 34.6v5.4M36.5 34.6v5.4"/></g>'
        # ---- lit window with a glowing text-input cursor (I-beam) ----
        f'<rect x="20.5" y="26" width="11" height="12" rx="0.6" fill="#0c0f14" stroke="{MORTAR}" stroke-width="0.7"/>'
        f'<g stroke="{PINK}" stroke-width="2.6" stroke-linecap="round" opacity="0.35">'
        f'<path d="M26 28.4v7.2"/></g>'   # cursor glow
        f'<g stroke="{LB}" stroke-width="1.3" stroke-linecap="round">'
        f'<path d="M26 28.4v7.2"/><path d="M24.3 28.4h3.4"/><path d="M24.3 35.6h3.4"/></g>'
    )


_RING_SRC = Path("/usr/share/icons/hicolor/scalable/apps/linuxmint-logo-ring.svg")


def _logo_svg(ring_fill: str = None, overlay: str = "", defs: str = "") -> str:
    """Compose an LM logo from the Mint ring source: green monogram, and either a
    recoloured ring (ring_fill) or a voided ring with an `overlay` painted on top."""
    import re
    if not _RING_SRC.exists():
        return None
    t = _RING_SRC.read_text()

    def set_fill(text, pid, fill):
        m = re.search(r'<path\b[^>]*?id="' + re.escape(pid) + r'"[^>]*?>', text, re.S)
        if not m:
            return text
        el = re.sub(r'fill:#[0-9a-fA-F]+', 'fill:' + fill, m.group(0), count=1)
        return text[:m.start()] + el + text[m.end():]

    t = set_fill(t, "path4193-1-9", "#37ffa0")              # LM monogram -> mint
    t = set_fill(t, "path1374-2-6", ring_fill or "#0c0e12")  # ring fill or void
    if defs:
        t = t.replace('<defs\n     id="defs2" />', f'<defs id="defs2">{defs}</defs>')
    if overlay:
        t = t.replace('</svg>', overlay + '</svg>')
    return t


def _arc_ring(colors=("#ff5aa8", "#ffd24d", "#36c8ff", "#9b6cf2")) -> str:
    """Four hard-edged 90° arcs (each hue once, crisp boundaries) on the ring."""
    import math
    cx, cy, R, Wd, o = 12.634, 12.634, 11.62, 2.3, 1.5

    def pt(a):
        a = math.radians(a)
        return cx + R * math.sin(a), cy - R * math.cos(a)

    def arc(a1, a2, c):
        x1, y1 = pt(a1)
        x2, y2 = pt(a2)
        return (f'<path d="M {x1:.3f} {y1:.3f} A {R} {R} 0 0 1 {x2:.3f} {y2:.3f}" '
                f'fill="none" stroke="{c}" stroke-width="{Wd}" stroke-linecap="butt"/>')
    bounds = [(-45 - o, 45 + o), (45 - o, 135 + o), (135 - o, 225 + o), (225 - o, 315 + o)]
    return '<g>' + ''.join(arc(a, b, c) for (a, b), c in zip(bounds, colors)) + '</g>'


def logo_variants() -> dict:
    """Named LM-logo variants for the in-app gallery (all keep the green monogram)."""
    grad = ('<linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#ff5aa8"/>'
            '<stop offset="0.5" stop-color="#9b6cf2"/>'
            '<stop offset="1" stop-color="#36c8ff"/></linearGradient>')
    return {
        "aurora": _logo_svg(overlay=_arc_ring()),                       # pink/yellow/blue/violet arcs
        "gradient": _logo_svg(ring_fill="url(#g)", defs=grad),          # smooth pink->violet->blue
        "pink": _logo_svg(ring_fill=PINK),                             # solid pink
        "gold": _logo_svg(ring_fill=GOLD),                             # solid gold
        "ice": _logo_svg(ring_fill=LB),                                # light-blue
        "sunset": _logo_svg(overlay=_arc_ring(("#ff5aa8", "#ff8a4d", "#f1bf40", "#db3776"))),  # warm
    }


def make_logo(apps_dir: Path) -> None:
    """The default LM logo: the four-colour aurora ring + mint-green monogram."""
    t = _logo_svg(overlay=_arc_ring())
    if t:
        (apps_dir / "blossom-logo.svg").write_text(t)


def _flower_svg(petal_color: str, center_color: str, n: int = 5) -> str:
    petal = ("M24 21 C 18 21, 14.5 15.5, 17 9.5 C 18.2 6.6, 21 6, 22.6 8.4 "
             "L 24 10.6 L 25.4 8.4 C 27 6, 29.8 6.6, 31 9.5 C 33.5 15.5, 30 21, 24 21 Z")
    step = 360.0 / n
    petals = "".join(f'<path d="{petal}" fill="{petal_color}" '
                     f'transform="rotate({k*step:.2f} 24 24)"/>' for k in range(n))
    return _svg(f'<g>{petals}</g><circle cx="24" cy="24" r="3.2" fill="{center_color}"/>')


def flower_variants() -> dict:
    """Named bloom-button variants for the in-app gallery."""
    return {
        "sakura": _flower_svg("#f060a0", "#ffcf5a", 5),   # pink + gold (default)
        "sky": _flower_svg("#5bc8ff", "#eaf6ff", 5),      # blue + light
        "sun": _flower_svg("#f1bf40", "#db3776", 6),      # gold + pink, 6 petals
        "violet": _flower_svg("#9b6cf2", "#ffcf5a", 5),   # violet + gold
        "rose": _flower_svg("#db3776", "#f1bf40", 6),     # deep pink, 6 petals
        "frost": _flower_svg("#eaf6ff", "#9b6cf2", 8),    # white, 8 petals
    }


def make_flower(apps_dir: Path) -> None:
    """The default Blossom mark — a pink sakura with a gold centre."""
    (apps_dir / "blossom-flower.svg").write_text(_flower_svg("#f060a0", "#ffcf5a", 5))


def make_gallery(root: Path) -> None:
    """Write all logo + bloom-button variants under <repo>/gallery/ for the picker."""
    for kind, variants in (("logos", logo_variants()), ("flowers", flower_variants())):
        d = root / "gallery" / kind
        d.mkdir(parents=True, exist_ok=True)
        for name, svg in variants.items():
            if svg:
                (d / f"{name}.svg").write_text(svg)


def network() -> str:
    return _svg(
        f'<g fill="{BODY}" stroke="{LB}" stroke-width="1.6">'
        f'<rect x="19" y="13" width="10" height="7" rx="1.5"/>'
        f'<rect x="9" y="29" width="10" height="7" rx="1.5"/>'
        f'<rect x="29" y="29" width="10" height="7" rx="1.5"/></g>'
        f'<path d="M24 20v4M24 24H14v5M24 24h10v5" fill="none" stroke="{PINK}" stroke-width="1.6"/>'
    )


# ---- name → svg map (freedesktop icon names + aliases) ---------------------
def build():
    places = OUT / "places" / "scalable"
    devices = OUT / "devices" / "scalable"
    apps = OUT / "apps" / "scalable"
    for d in (places, devices, apps):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    make_logo(apps)
    make_flower(apps)
    make_gallery(OUT.parent.parent)   # gallery/logos + gallery/flowers variants

    # app icons we override (the rest inherit from Papirus-Dark)
    apps_icons = {
        "accessories-text-editor": editor(),   # xed
        "org.x.editor": editor(),
        "xed": editor(),
        "text-editor": editor(),
    }
    for name, svg in apps_icons.items():
        (apps / f"{name}.svg").write_text(svg)

    # folders (Places)
    folders = {
        "folder": folder(),
        "folder-open": folder(),
        "inode-directory": folder(),
        "folder-new": folder(),
        "folder-visiting": folder(),
        "folder-blue": folder(),
        "folder-tar": folder(GLYPHS["templates"]),
        "folder-documents": folder(GLYPHS["documents"]),
        "folder-download": folder(GLYPHS["download"]),
        "folder-downloads": folder(GLYPHS["download"]),
        "folder-music": folder(GLYPHS["music"]),
        "folder-pictures": folder(GLYPHS["pictures"]),
        "folder-videos": folder(GLYPHS["videos"]),
        "folder-publicshare": folder(GLYPHS["publicshare"]),
        "folder-templates": folder(GLYPHS["templates"]),
        "folder-recent": folder(GLYPHS["recent"], top=GOLD),
        "folder-saved-search": folder(GLYPHS["search"]),
        "folder-drag-accept": folder(GLYPHS["drag"], top=GOLD),
        "folder-remote": folder(GLYPHS["publicshare"]),
        "folder-home": folder(GLYPHS["home"], top=GOLD),
        "user-home": folder(GLYPHS["home"], top=GOLD),
        "user-desktop": folder(GLYPHS["desktop"]),
        "user-bookmarks": folder(GLYPHS["templates"], top=GOLD),
        "network-workgroup": network(),
        "network-server": network(),
        "user-trash": trash(False),
        "user-trash-full": trash(True),
    }
    for name, svg in folders.items():
        (places / f"{name}.svg").write_text(svg)

    # devices
    devs = {
        "drive-harddisk": harddisk(),
        "drive-harddisk-usb": harddisk(),
        "drive-removable-media": usb(),
        "drive-removable-media-usb": usb(),
        "media-removable": usb(),
        "media-flash": usb(),
        "drive-optical": optical(),
        "media-optical": optical(),
        "computer": computer(),
    }
    for name, svg in devs.items():
        (devices / f"{name}.svg").write_text(svg)

    # index.theme (scalable)
    index = """[Icon Theme]
Name=Blossom
Comment=AMOLED pink — void-dark folders with a pink header and light-blue glyphs
Inherits=Papirus-Dark,Mint-Y,Adwaita,gnome,hicolor

Directories=places/scalable,devices/scalable,apps/scalable

[places/scalable]
MinSize=8
MaxSize=512
Size=48
Context=Places
Type=Scalable

[devices/scalable]
MinSize=8
MaxSize=512
Size=48
Context=Devices
Type=Scalable

[apps/scalable]
MinSize=8
MaxSize=512
Size=48
Context=Applications
Type=Scalable
"""
    (OUT / "index.theme").write_text(index)
    n = len(folders) + len(devs)
    print(f"Blossom icons: wrote {n} icons to {OUT}")


if __name__ == "__main__":
    build()
