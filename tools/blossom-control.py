#!/usr/bin/env python3
"""
Blossom Control — a tabbed GTK panel/GUI for the Blossom theme.

A single Blossom-themed GTK window that drives the theme's tools: applying the
look, icon-pack rotation, taskbar accent, panel corner-glow, fonts, and picking
the menu logo / bloom-button mark from an in-app gallery. Because it's a GTK app
it is themed by Blossom itself — the control surface looks like what it controls.

Run:  python3 tools/blossom-control.py
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib  # noqa: E402

import glob
import json
import os
import re
import struct
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTATE = os.path.join(ROOT, "tools", "blossom-rotate.py")
GLOW_SCRIPT = os.path.join(ROOT, "tools", "blossom-glow.py")
LOGO = os.path.join(ROOT, "icons", "Blossom", "apps", "scalable", "blossom-flower.svg")
CINNAMON_CSS = os.path.join(ROOT, "cinnamon", "cinnamon.css")
GALLERY = os.path.join(ROOT, "gallery")
BLOSSOM_LOGO = os.path.join(ROOT, "icons", "Blossom", "apps", "scalable", "blossom-logo.svg")
BLOSSOM_FLOWER = os.path.join(ROOT, "icons", "Blossom", "apps", "scalable", "blossom-flower.svg")
STATE = os.path.expanduser("~/.local/share/blossom-rotate/state.json")
BACKUP = os.path.expanduser("~/.local/share/blossom/look-backup.json")
FOCUS_BACKUP = os.path.expanduser("~/.local/share/blossom/focus-backup.json")
GLOW_CFG = os.path.expanduser("~/.local/share/blossom/glow.json")

ICON_DIRS = [os.path.expanduser("~/.icons"),
             os.path.expanduser("~/.local/share/icons"), "/usr/share/icons"]

LOOK = [
    ("org.cinnamon.theme", "name"),                       # shell
    ("org.cinnamon.desktop.interface", "gtk-theme"),      # apps
    ("org.cinnamon.desktop.wm.preferences", "theme"),     # window borders
    ("org.cinnamon.desktop.interface", "icon-theme"),     # icons
]

PALETTE = [
    ("pink", "#db3776"), ("gold", "#f1bf40"), ("light", "#eaf6ff"),
    ("red", "#ec4e53"), ("void", "#000000"),
]
FONTS = ["Ubuntu 10", "Noto Sans 10", "Inter 10", "Lexend 10"]

# Taskbar accents — (label, key, kind, payload). kind "border" -> (top,bottom,left,
# right) widths (pink colour comes from the theme's :active rule). kind "image" ->
# an SVG under common-assets/accent/ stretched over the active item (100% x 100%),
# the only way to draw partial-length shapes (CSS borders are full-length).
ACCENTS = [
    ("Bottom (default)", "bottom", "border", (0, 2, 0, 0)),
    ("Top", "top", "border", (2, 0, 0, 0)),
    ("L-shape (full)", "lfull", "border", (0, 2, 2, 0)),
]
ACCENT_SELECTORS = (
    ".grouped-window-list-item-box.top, .grouped-window-list-item-box.bottom,\n"
    ".grouped-window-list-item-box.left, .grouped-window-list-item-box.right,\n"
    ".window-list-item-box.top, .window-list-item-box.bottom,\n"
    ".window-list-item-box.left, .window-list-item-box.right"
)
ACCENT_ACTIVE_SELECTORS = (
    ".grouped-window-list-item-box:active, .grouped-window-list-item-box:checked,\n"
    ".grouped-window-list-item-box:focus,\n"
    ".window-list-item-box:active, .window-list-item-box:checked,\n"
    ".window-list-item-box:focus, .window-list-item-box:running"
)

# Panel glow
GLOW_CORNERS = [("Top-left", "tl"), ("Top-right", "tr"),
                ("Bottom-left", "bl"), ("Bottom-right", "br")]
GLOW_PRESETS = [("Pink", "#ff5aa8"), ("Gold", "#ffc846"), ("Blue", "#3cc8ff"),
                ("Violet", "#9669f2"), ("Red", "#ec4e53"), ("Mint", "#37ffa0"),
                ("Light", "#eaf6ff")]
GLOW_DEFAULT = {"tl": ("#ff5aa8", 0.85), "tr": ("#3cc8ff", 0.85),
                "bl": ("#ffc846", 0.85), "br": ("#9669f2", 0.85)}


def gget(schema, key):
    return subprocess.run(["gsettings", "get", schema, key],
                          capture_output=True, text=True).stdout.strip().strip("'")


def gset(schema, key, val):
    subprocess.run(["gsettings", "set", schema, key, val], check=False)


def rotate(*args):
    return subprocess.run(["python3", ROTATE, *args],
                          capture_output=True, text=True).stdout.strip()


def cinnamon(method, *args):
    """Call an org.Cinnamon dbus method (ReloadTheme / ReloadXlet)."""
    cmd = ["dbus-send", "--session", "--dest=org.Cinnamon", "--type=method_call",
           "/org/Cinnamon", f"org.Cinnamon.{method}"]
    cmd += [f"string:{a}" for a in args]
    subprocess.run(cmd, check=False, capture_output=True)


def reload_theme():
    cinnamon("ReloadTheme")


def refresh_icons():
    """Make Cinnamon re-render theme icons after a logo/flower file is swapped.
    St caches rendered icons by name, and ReloadXlet alone won't drop that — only
    a real icon-theme change does. Flash through another *installed* theme (not
    blank hicolor) so the blink shows real icons, then return."""
    subprocess.run(["gtk-update-icon-cache", "-f", "-t",
                    os.path.expanduser("~/.icons/Blossom")],
                   check=False, capture_output=True)
    cur = gget("org.cinnamon.desktop.interface", "icon-theme") or "Blossom"
    inst = set(icon_themes())
    tmp = next((t for t in ("Mint-Y-Sand", "Mint-Y", "Mint-X", "Adwaita")
                if t in inst and t != cur), "hicolor")
    gset("org.cinnamon.desktop.interface", "icon-theme", tmp)
    time.sleep(0.35)
    gset("org.cinnamon.desktop.interface", "icon-theme", cur)


def icon_themes():
    seen, out = set(), []
    for d in ICON_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            idx = os.path.join(d, name, "index.theme")
            if name in seen or not os.path.isfile(idx):
                continue
            try:
                with open(idx, errors="ignore") as fh:
                    txt = fh.read()
            except OSError:
                continue
            if "Directories=" in txt:
                seen.add(name)
                out.append(name)
    return out


def accent_block(key, kind, payload):
    head = (f"/* BLOSSOM-ACCENT:{key} */\n"
            "/* Managed by Blossom Control (Taskbar accent). Appended last so it\n"
            "   overrides the panel-position rules; grouped + plain applets. */\n")
    if kind == "border":
        t, b, l, r = payload
        body = (f"{ACCENT_SELECTORS} {{\n"
                f"  border-top-width: {t}px;\n  border-bottom-width: {b}px;\n"
                f"  border-left-width: {l}px;\n  border-right-width: {r}px;\n"
                f"  background-image: none; }}\n"
                f"{ACCENT_ACTIVE_SELECTORS} {{ background-image: none; }}\n")
    else:
        body = (f"{ACCENT_SELECTORS} {{ border-width: 0; background-image: none; }}\n"
                f"{ACCENT_ACTIVE_SELECTORS} {{\n  border-width: 0;\n"
                f"  background-image: url(\"common-assets/accent/{payload}\");\n"
                f"  background-size: 100% 100%;\n  background-repeat: no-repeat;\n"
                f"  background-position: center; }}\n")
    return head + body + "/* BLOSSOM-ACCENT-END */"


def current_accent():
    try:
        m = re.search(r"/\* BLOSSOM-ACCENT:(\w+) \*/", open(CINNAMON_CSS).read())
        return m.group(1) if m else "bottom"
    except OSError:
        return "bottom"


def glow_load():
    cfg = {"enabled": True, "corners": {k: {"color": c, "intensity": i}
                                        for k, (c, i) in GLOW_DEFAULT.items()}}
    if os.path.exists(GLOW_CFG):
        try:
            u = json.load(open(GLOW_CFG))
            cfg["enabled"] = u.get("enabled", True)
            for k, v in u.get("corners", {}).items():
                cfg["corners"].setdefault(k, {}).update(v)
        except (ValueError, OSError):
            pass
    return cfg


def panel_launchers_json():
    g = glob.glob(os.path.expanduser(
        "~/.config/cinnamon/spices/panel-launchers@cinnamon.org/*.json"))
    return g[0] if g else None


def rgba(hexv):
    c = Gdk.RGBA()
    c.parse(hexv)
    return c


def rgba_hex(c):
    return "#%02x%02x%02x" % (int(c.red * 255), int(c.green * 255), int(c.blue * 255))


def cursor_themes():
    """(name, dir) for every installed cursor theme; Blossom-* sorted first."""
    out, seen = [], set()
    for d in ICON_DIRS:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name in seen:
                continue
            if os.path.isdir(os.path.join(d, name, "cursors")):
                seen.add(name)
                out.append((name, os.path.join(d, name)))
    out.sort(key=lambda t: (not t[0].startswith("Blossom"), t[0].lower()))
    return out


def cursor_pixbuf(theme_dir, target=44):
    """Render a cursor theme's arrow to a GdkPixbuf for the gallery tiles.

    Parses the Xcursor binary directly (no extra tooling), picks the image
    nearest `target` px, and un-premultiplies it for a straight-alpha pixbuf."""
    path = None
    for cand in ("left_ptr", "default", "arrow"):
        p = os.path.join(theme_dir, "cursors", cand)
        if os.path.isfile(p):
            path = p
            break
    if not path:
        return None
    try:
        b = open(path, "rb").read()
        magic, hsize, _ver, ntoc = struct.unpack_from("<4sIII", b, 0)
        if magic != b"Xcur":
            return None
        off, imgs = hsize, []
        for _ in range(ntoc):
            t, s, pos = struct.unpack_from("<III", b, off)
            off += 12
            if t == 0xfffd0002:
                imgs.append((s, pos))
        if not imgs:
            return None
        _s, pos = min(imgs, key=lambda z: abs(z[0] - target))
        ch, _ct, _cs, _cv, w, h, _xh, _yh, _dly = struct.unpack_from("<IIIIIIIII", b, pos)
        px = pos + ch
        out = bytearray(w * h * 4)
        for i in range(w * h):
            o = px + i * 4
            B, G, R, A = b[o], b[o + 1], b[o + 2], b[o + 3]
            if A:                       # un-premultiply for straight-alpha pixbuf
                R = min(255, R * 255 // A)
                G = min(255, G * 255 // A)
                B = min(255, B * 255 // A)
            out[i * 4], out[i * 4 + 1], out[i * 4 + 2], out[i * 4 + 3] = R, G, B, A
        return GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(bytes(out)), GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4)
    except Exception:
        return None


class Control(Gtk.Window):
    def __init__(self):
        super().__init__(title="Blossom")
        self.set_wmclass("blossom-control", "blossom-control")
        self.set_role("blossom-control")
        self.set_default_size(480, -1)
        self.set_position(Gtk.WindowPosition.NONE)
        self._loading = True
        try:
            self.set_icon_from_file(LOGO)
        except Exception:
            pass

        hb = Gtk.HeaderBar(show_close_button=True)
        hb.props.title = "Blossom"
        hb.props.subtitle = "theme control"
        try:
            px = GdkPixbuf.Pixbuf.new_from_file_at_size(LOGO, 24, 24)
            hb.pack_start(Gtk.Image.new_from_pixbuf(px))
        except Exception:
            pass
        self.set_titlebar(hb)

        nb = Gtk.Notebook()
        nb.set_border_width(8)
        self.add(nb)
        nb.append_page(self._tab(self._look_tab()), Gtk.Label(label="Look"))
        nb.append_page(self._tab(self._taskbar_tab()), Gtk.Label(label="Taskbar"))
        nb.append_page(self._tab(self._logos_tab()), Gtk.Label(label="Logos"))
        nb.append_page(self._tab(self._icons_tab()), Gtk.Label(label="Icons"))
        nb.append_page(self._tab(self._cursor_tab()), Gtk.Label(label="Cursor"))

        self._loading = False
        self.refresh()

    # -- builders -------------------------------------------------------
    def _tab(self, child):
        child.set_border_width(12)
        return child

    def _frame(self, title, child):
        f = Gtk.Frame()
        lbl = Gtk.Label()
        lbl.set_markup(f"  <b>{title}</b>  ")
        f.set_label_widget(lbl)
        child.set_border_width(12)
        f.add(child)
        return f

    def _btn(self, label, cb, suggested=False):
        b = Gtk.Button(label=label)
        if suggested:
            b.get_style_context().add_class("suggested-action")
        b.connect("clicked", cb)
        return b

    # ---- Look tab -----------------------------------------------------
    def _look_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        look = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.look_lbl = Gtk.Label(xalign=0)
        self.look_lbl.set_line_wrap(True)
        look.add(self.look_lbl)
        row = Gtk.Box(spacing=8)
        row.add(self._btn("Apply Blossom", self.on_apply, suggested=True))
        row.add(self._btn("Revert", self.on_revert))
        look.add(row)
        self.focus_btn = Gtk.CheckButton(
            label="Focus mode — hide desktop icons + mute notifications")
        self.focus_btn.connect("toggled", self.on_focus)
        look.add(self.focus_btn)
        box.add(self._frame("Look", look))

        pal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        prow = Gtk.Box(spacing=8, homogeneous=True)
        for name, hexv in PALETTE:
            prow.add(self._swatch(name, hexv))
        pal.add(prow)
        self.copied_lbl = Gtk.Label(xalign=0)
        self.copied_lbl.set_markup("<small>click a swatch to copy its hex</small>")
        pal.add(self.copied_lbl)
        box.add(self._frame("Palette", pal))

        fb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fb.add(Gtk.Label(xalign=0, label="Desktop & app font"))
        self.font_combo = Gtk.ComboBoxText()
        self.font_combo.connect("changed", self.on_font)
        fb.add(self.font_combo)
        box.add(self._frame("Typeface", fb))
        return box

    def _swatch(self, name, hexv):
        btn = Gtk.Button()
        btn.set_size_request(-1, 40)
        btn.set_tooltip_text(f"{name}  {hexv}  — click to copy")
        light = hexv.lower() in ("#000000", "#db3776", "#ec4e53")
        fg = "#eaf6ff" if light else "#101010"
        prov = Gtk.CssProvider()
        prov.load_from_data((
            f"button {{ background-image:none; background-color:{hexv};"
            f" color:{fg}; border:1px solid rgba(234,246,255,0.18);"
            f" border-radius:6px; font-weight:bold; }}").encode())
        btn.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        btn.set_label(hexv)
        btn.connect("clicked", self.on_copy, hexv)
        return btn

    # ---- Taskbar tab --------------------------------------------------
    def _taskbar_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        acc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        acc.add(Gtk.Label(xalign=0,
                          label="Where the pink open-app accent sits on the taskbar"))
        self.accent_combo = Gtk.ComboBoxText()
        for label, key, _k, _p in ACCENTS:
            self.accent_combo.append(key, label)
        self.accent_combo.connect("changed", self.on_accent)
        acc.add(self.accent_combo)
        box.add(self._frame("Taskbar accent", acc))

        # ---- panel glow ----
        gl = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.glow_on = Gtk.CheckButton(label="Glow the panel's four corners")
        self.glow_on.connect("toggled", lambda *_: self._glow_sensitive())
        gl.add(self.glow_on)
        grid = Gtk.Grid(column_spacing=8, row_spacing=6)
        self.glow_color = {}
        self.glow_scale = {}
        presets = [rgba(h) for _n, h in GLOW_PRESETS]
        for i, (label, key) in enumerate(GLOW_CORNERS):
            grid.attach(Gtk.Label(label=label, xalign=0), 0, i, 1, 1)
            cb = Gtk.ColorButton()
            cb.set_title(f"{label} glow colour")
            cb.add_palette(Gtk.Orientation.HORIZONTAL, len(presets), presets)
            self.glow_color[key] = cb
            grid.attach(cb, 1, i, 1, 1)
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
            sc.set_value(85)
            sc.set_hexpand(True)
            sc.set_size_request(150, -1)
            sc.set_draw_value(False)
            self.glow_scale[key] = sc
            grid.attach(sc, 2, i, 1, 1)
        gl.add(grid)
        grow = Gtk.Box(spacing=8)
        grow.add(self._btn("Apply glow", self.on_glow_apply, suggested=True))
        gl.add(grow)
        gl.add(Gtk.Label(xalign=0, label="", wrap=True))
        self._glow_help = gl.get_children()[-1]
        self._glow_help.set_markup("<small>colour button has presets — "
                                   "click + to save a custom one. slider = intensity.</small>")
        box.add(self._frame("Panel corner glow", gl))
        return box

    def _glow_sensitive(self):
        on = self.glow_on.get_active()
        for k in self.glow_color:
            self.glow_color[k].set_sensitive(on)
            self.glow_scale[k].set_sensitive(on)

    # ---- Logos tab ----------------------------------------------------
    def _logos_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        lg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lg.add(Gtk.Label(xalign=0, label="Pick the start-menu logo"))
        lg.add(self._gallery("logos", self.on_pick_logo))
        box.add(self._frame("Menu logo", lg))

        fl = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.bloom_on = Gtk.CheckButton(label="Show the bloom button on the panel")
        self.bloom_on.connect("toggled", self.on_bloom_toggle)
        fl.add(self.bloom_on)
        fl.add(Gtk.Label(xalign=0, label="Pick the bloom-button mark"))
        fl.add(self._gallery("flowers", self.on_pick_flower))
        box.add(self._frame("Bloom button", fl))
        self.logo_note = Gtk.Label(xalign=0)
        self.logo_note.set_markup("<small>click a tile to apply it</small>")
        box.add(self.logo_note)
        return box

    def _gallery(self, kind, cb):
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(6)
        flow.set_min_children_per_line(3)
        flow.set_column_spacing(6)
        flow.set_row_spacing(6)
        for path in sorted(glob.glob(os.path.join(GALLERY, kind, "*.svg"))):
            name = os.path.splitext(os.path.basename(path))[0]
            b = Gtk.Button()
            b.set_tooltip_text(name)
            b.set_relief(Gtk.ReliefStyle.NONE)
            try:
                px = GdkPixbuf.Pixbuf.new_from_file_at_size(path, 56, 56)
                b.set_image(Gtk.Image.new_from_pixbuf(px))
                b.set_always_show_image(True)
            except Exception:
                b.set_label(name)
            b.connect("clicked", lambda _w, n=name: cb(n))
            flow.add(b)
        return flow

    # ---- Icons tab ----------------------------------------------------
    def _icons_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.rot_lbl = Gtk.Label(xalign=0)
        box.add(self.rot_lbl)
        pick = Gtk.Box(spacing=8)
        pick.add(Gtk.Label(label="Pack:"))
        self.pack_combo = Gtk.ComboBoxText()
        self.pack_combo.set_hexpand(True)
        self.pack_combo.connect("changed", self.on_pick_pack)
        pick.add(self.pack_combo)
        box.add(pick)
        row = Gtk.Box(spacing=8)
        row.add(self._btn("\U0001F500  Shuffle pack", self.on_shuffle))
        row.add(self._btn("♥  Like", self.on_like, suggested=True))
        row.add(self._btn("✕  Dislike", self.on_dislike))
        box.add(row)
        self.taste = Gtk.Label(xalign=0)
        _mono = Gtk.CssProvider()
        _mono.load_from_data(b"label { font-family: monospace; font-size: 9pt; }")
        self.taste.get_style_context().add_provider(_mono, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box.add(self.taste)
        self.auto = Gtk.CheckButton(label="Rotate once per login")
        self.auto.connect("toggled", self.on_auto)
        box.add(self.auto)
        return self._frame("Icon rotation", box)

    # ---- Cursor tab ---------------------------------------------------
    def _cursor_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.cursor_lbl = Gtk.Label(xalign=0)
        box.add(self.cursor_lbl)

        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(2)
        flow.set_column_spacing(6)
        flow.set_row_spacing(6)
        for name, d in cursor_themes():
            b = Gtk.Button()
            b.set_relief(Gtk.ReliefStyle.NONE)
            b.set_tooltip_text(name)
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            pb = cursor_pixbuf(d, 44)
            if pb is not None:
                cell.add(Gtk.Image.new_from_pixbuf(pb))
            lab = Gtk.Label(label=name.replace("Blossom-", "❀ "))
            lab.set_max_width_chars(14)
            cell.add(lab)
            b.add(cell)
            b.connect("clicked", lambda _w, n=name: self.on_pick_cursor(n))
            flow.add(b)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(220)
        sw.add(flow)
        box.add(self._frame("Pointer theme", sw))

        sz = Gtk.Box(spacing=8)
        sz.add(Gtk.Label(label="Pointer size"))
        self.cursor_size = Gtk.SpinButton.new_with_range(16, 64, 2)
        self.cursor_size.connect("value-changed", self.on_cursor_size)
        sz.add(self.cursor_size)
        box.add(self._frame("Size", sz))

        note = Gtk.Label(xalign=0)
        note.set_line_wrap(True)
        note.set_markup("<small>click a pointer to apply · ❀ Blossom variants are "
                        "recoloured from your Bibata · new windows update instantly, "
                        "a re-login applies it everywhere</small>")
        box.add(note)
        return box

    # -- state ----------------------------------------------------------
    def refresh(self):
        self._loading = True
        cur = {k[1]: gget(k[0], k[1]) for k in LOOK}
        self.look_lbl.set_markup(
            f"shell: <b>{cur.get('name')}</b>   icons: <b>{cur.get('icon-theme')}</b>\n"
            f"gtk: {cur.get('gtk-theme')}   wm: {cur.get('theme')}")

        self.font_combo.remove_all()
        font_now = gget("org.cinnamon.desktop.interface", "font-name")
        opts = list(FONTS)
        if font_now and font_now not in opts:
            opts.insert(0, font_now)
        for f in opts:
            self.font_combo.append_text(f)
        if font_now in opts:
            self.font_combo.set_active(opts.index(font_now))

        self.accent_combo.set_active_id(current_accent())

        g = glow_load()
        self.glow_on.set_active(g["enabled"])
        for k in self.glow_color:
            c = g["corners"].get(k, {})
            self.glow_color[k].set_rgba(rgba(c.get("color", "#000000")))
            self.glow_scale[k].set_value(float(c.get("intensity", 0.0)) * 100)
        self._glow_sensitive()

        self.bloom_on.set_active(self._bloom_enabled())

        icon = gget("org.cinnamon.desktop.interface", "icon-theme")
        self.rot_lbl.set_markup(f"current pack: <b>{icon}</b>")
        self.pack_combo.remove_all()
        themes = icon_themes()
        if icon and icon not in themes:
            themes.insert(0, icon)
        for t in themes:
            self.pack_combo.append_text(t)
        if icon in themes:
            self.pack_combo.set_active(themes.index(icon))

        tally = {}
        if os.path.exists(STATE):
            for h in json.load(open(STATE)).get("history", []):
                if h.get("liked"):
                    tally[h["theme"]] = tally.get(h["theme"], 0) + 1
        if tally:
            lines = "\n".join(f"  {'♥'*min(n,8)}  {t} ({n})"
                              for t, n in sorted(tally.items(), key=lambda x: -x[1]))
            self.taste.set_text("liked packs:\n" + lines)
        else:
            self.taste.set_text("liked packs: none yet — hit ♥ on a day you like")
        self.auto.set_active(os.path.exists(
            os.path.expanduser("~/.config/autostart/blossom-rotate.desktop")))
        self.focus_btn.set_active(os.path.exists(FOCUS_BACKUP))

        ctheme = gget("org.cinnamon.desktop.interface", "cursor-theme")
        self.cursor_lbl.set_markup(f"current pointer: <b>{ctheme}</b>")
        try:
            self.cursor_size.set_value(int(gget("org.cinnamon.desktop.interface", "cursor-size") or 24))
        except (TypeError, ValueError):
            self.cursor_size.set_value(24)
        self._loading = False

    def position_lower_left(self):
        disp = Gdk.Display.get_default()
        mon = disp.get_primary_monitor() or disp.get_monitor(0)
        wa = mon.get_workarea()
        _w, win_h = self.get_size()
        self.move(wa.x + 56, wa.y + wa.height - win_h - 56)

    # -- actions: look --------------------------------------------------
    def on_apply(self, _):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        json.dump({k[1]: gget(k[0], k[1]) for k in LOOK}, open(BACKUP, "w"))
        for schema, key in LOOK:
            gset(schema, key, "Blossom")
        self.refresh()

    def on_revert(self, _):
        if os.path.exists(BACKUP):
            saved = json.load(open(BACKUP))
            for schema, key in LOOK:
                if saved.get(key):
                    gset(schema, key, saved[key])
        self.refresh()

    def on_copy(self, _btn, hexv):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clip.set_text(hexv, -1)
        clip.store()
        self.copied_lbl.set_markup(f"<small>copied <b>{hexv}</b> to clipboard</small>")

    def on_font(self, combo):
        if self._loading:
            return
        val = combo.get_active_text()
        # only act on a real user change, never re-apply the current value
        if val and val != gget("org.cinnamon.desktop.interface", "font-name"):
            gset("org.cinnamon.desktop.interface", "font-name", val)
            gset("org.gnome.desktop.interface", "font-name", val)

    def on_focus(self, btn):
        if self._loading:
            return
        if btn.get_active():
            os.makedirs(os.path.dirname(FOCUS_BACKUP), exist_ok=True)
            json.dump({"icons": gget("org.nemo.desktop", "show-desktop-icons"),
                       "notify": gget("org.cinnamon.desktop.notifications",
                                      "display-notifications")}, open(FOCUS_BACKUP, "w"))
            gset("org.nemo.desktop", "show-desktop-icons", "false")
            gset("org.cinnamon.desktop.notifications", "display-notifications", "false")
        else:
            saved = {}
            if os.path.exists(FOCUS_BACKUP):
                saved = json.load(open(FOCUS_BACKUP))
                os.remove(FOCUS_BACKUP)
            gset("org.nemo.desktop", "show-desktop-icons", saved.get("icons", "true"))
            gset("org.cinnamon.desktop.notifications", "display-notifications",
                 saved.get("notify", "true"))

    # -- actions: taskbar ----------------------------------------------
    def on_accent(self, combo):
        if self._loading:
            return
        key = combo.get_active_id()
        if not key or key == current_accent():   # never re-apply the current value
            return
        spec = next(((kd, pl) for _l, k, kd, pl in ACCENTS if k == key), None)
        if not spec:
            return
        try:
            css = open(CINNAMON_CSS).read()
        except OSError:
            return
        block = accent_block(key, spec[0], spec[1])
        pat = re.compile(r"/\* BLOSSOM-ACCENT:.*?/\* BLOSSOM-ACCENT-END \*/", re.S)
        css = pat.sub(block, css, count=1) if pat.search(css) else css + "\n\n" + block + "\n"
        open(CINNAMON_CSS, "w").write(css)
        reload_theme()

    def on_glow_apply(self, _):
        cfg = {"enabled": self.glow_on.get_active(), "corners": {}}
        for k in self.glow_color:
            cfg["corners"][k] = {"color": rgba_hex(self.glow_color[k].get_rgba()),
                                 "intensity": round(self.glow_scale[k].get_value() / 100, 3)}
        os.makedirs(os.path.dirname(GLOW_CFG), exist_ok=True)
        json.dump(cfg, open(GLOW_CFG, "w"), indent=2)
        subprocess.run(["python3", GLOW_SCRIPT], check=False, capture_output=True)
        reload_theme()

    # -- actions: logos -------------------------------------------------
    def on_pick_logo(self, name):
        src = os.path.join(GALLERY, "logos", f"{name}.svg")
        if os.path.exists(src):
            open(BLOSSOM_LOGO, "w").write(open(src).read())
            refresh_icons()
            self.logo_note.set_markup(f"<small>menu logo → <b>{name}</b></small>")

    def on_pick_flower(self, name):
        src = os.path.join(GALLERY, "flowers", f"{name}.svg")
        if os.path.exists(src):
            open(BLOSSOM_FLOWER, "w").write(open(src).read())
            refresh_icons()
            self.logo_note.set_markup(f"<small>bloom button → <b>{name}</b></small>")

    def _bloom_enabled(self):
        f = panel_launchers_json()
        if not f:
            return False
        try:
            d = json.load(open(f))
            return "blossom-control.desktop" in d.get("launcherList", {}).get("value", [])
        except (ValueError, OSError):
            return False

    def on_bloom_toggle(self, btn):
        if self._loading:
            return
        f = panel_launchers_json()
        if not f:
            return
        try:
            d = json.load(open(f))
        except (ValueError, OSError):
            return
        lst = d.setdefault("launcherList", {}).setdefault("value", [])
        if btn.get_active():
            if "blossom-control.desktop" not in lst:
                lst.append("blossom-control.desktop")
        else:
            d["launcherList"]["value"] = [x for x in lst if x != "blossom-control.desktop"]
        json.dump(d, open(f, "w"), indent=4)
        cinnamon("ReloadXlet", "panel-launchers@cinnamon.org", "APPLET")

    # -- actions: icons -------------------------------------------------
    def on_pick_pack(self, combo):
        if self._loading:
            return
        name = combo.get_active_text()
        # only act on a real user change, never re-apply the current pack
        if name and name != gget("org.cinnamon.desktop.interface", "icon-theme"):
            rotate("set", name)
            self.refresh()

    def on_shuffle(self, _):
        rotate("shuffle"); self.refresh()

    def on_like(self, _):
        rotate("like"); self.refresh()

    def on_dislike(self, _):
        rotate("dislike"); self.refresh()

    def on_auto(self, btn):
        if self._loading:
            return
        rotate("install" if btn.get_active() else "uninstall")

    # -- actions: cursor ------------------------------------------------
    def on_pick_cursor(self, name):
        for schema in ("org.cinnamon.desktop.interface", "org.gnome.desktop.interface"):
            gset(schema, "cursor-theme", name)
        self.cursor_lbl.set_markup(f"current pointer: <b>{name}</b>")

    def on_cursor_size(self, spin):
        if self._loading:
            return
        val = str(int(spin.get_value()))
        for schema in ("org.cinnamon.desktop.interface", "org.gnome.desktop.interface"):
            gset(schema, "cursor-size", val)


def main():
    GLib.set_prgname("blossom-control")
    win = Control()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    win.position_lower_left()
    Gtk.main()


if __name__ == "__main__":
    main()
