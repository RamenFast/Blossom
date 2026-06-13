#!/usr/bin/env python3
"""
Blossom Control — a tiny GTK panel/GUI for the Blossom theme.

It's the reusable pattern for the "lots of little one-off UIs" idea: a single
Blossom-themed GTK window that drives the theme's command-line tools (icon-pack
rotation + applying the look). Because it's a GTK app it is themed by Blossom
itself — so the control surface always looks like the thing it controls.

Run:  python3 tools/blossom-control.py
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Pango  # noqa: E402

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTATE = os.path.join(ROOT, "tools", "blossom-rotate.py")
LOGO = os.path.join(ROOT, "icons", "Blossom", "apps", "scalable", "blossom-flower.svg")
STATE = os.path.expanduser("~/.local/share/blossom-rotate/state.json")
BACKUP = os.path.expanduser("~/.local/share/blossom/look-backup.json")

LOOK = [
    ("org.cinnamon.theme", "name"),                       # shell
    ("org.cinnamon.desktop.interface", "gtk-theme"),      # apps
    ("org.cinnamon.desktop.wm.preferences", "theme"),     # window borders
    ("org.cinnamon.desktop.interface", "icon-theme"),     # icons
]


def gget(schema, key):
    return subprocess.run(["gsettings", "get", schema, key],
                          capture_output=True, text=True).stdout.strip().strip("'")


def gset(schema, key, val):
    subprocess.run(["gsettings", "set", schema, key, val], check=False)


def rotate(*args):
    return subprocess.run(["python3", ROTATE, *args],
                          capture_output=True, text=True).stdout.strip()


class Control(Gtk.Window):
    def __init__(self):
        super().__init__(title="Blossom")
        self.set_default_size(440, -1)
        self.set_border_width(0)
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

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_border_width(16)
        self.add(outer)

        # ---- Look ----
        outer.add(self._frame("Look", self._look_section()))
        # ---- Icon rotation ----
        outer.add(self._frame("Icon rotation", self._rotation_section()))

        self.refresh()

    # -- builders -------------------------------------------------------
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

    def _look_section(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.look_lbl = Gtk.Label(xalign=0)
        self.look_lbl.set_line_wrap(True)
        box.add(self.look_lbl)
        row = Gtk.Box(spacing=8)
        row.add(self._btn("Apply Blossom", self.on_apply, suggested=True))
        row.add(self._btn("Revert", self.on_revert))
        box.add(row)
        return box

    def _rotation_section(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.rot_lbl = Gtk.Label(xalign=0)
        box.add(self.rot_lbl)

        row = Gtk.Box(spacing=8)
        row.add(self._btn("⏭  Next pack", self.on_next))
        row.add(self._btn("♥  Like", self.on_like, suggested=True))
        row.add(self._btn("✕  Dislike", self.on_dislike))
        box.add(row)

        self.taste = Gtk.Label(xalign=0)
        self.taste.modify_font(Pango.FontDescription("monospace 9"))
        box.add(self.taste)

        self.auto = Gtk.CheckButton(label="Rotate once per login")
        self.auto.connect("toggled", self.on_auto)
        box.add(self.auto)
        return box

    # -- state ----------------------------------------------------------
    def refresh(self):
        cur = {k[1]: gget(k[0], k[1]) for k in LOOK}
        self.look_lbl.set_markup(
            f"shell: <b>{cur.get('name')}</b>   icons: <b>{cur.get('icon-theme')}</b>\n"
            f"gtk: {cur.get('gtk-theme')}   wm: {cur.get('theme')}")

        icon = gget("org.cinnamon.desktop.interface", "icon-theme")
        self.rot_lbl.set_markup(f"current pack: <b>{icon}</b>")

        tally = {}
        if os.path.exists(STATE):
            hist = json.load(open(STATE)).get("history", [])
            for h in hist:
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

    # -- actions --------------------------------------------------------
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

    def on_next(self, _):
        rotate("next"); self.refresh()

    def on_like(self, _):
        rotate("like"); self.refresh()

    def on_dislike(self, _):
        rotate("dislike"); self.refresh()

    def on_auto(self, btn):
        rotate("install" if btn.get_active() else "uninstall")


def main():
    win = Control()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
