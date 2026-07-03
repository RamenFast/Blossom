#!/usr/bin/env python3
"""
blossom-glow — generate the panel corner-glow PNG from a settings file.

Four LM-logo colours glow out of the bottom panel's corners. Everything is driven
by ~/.local/share/blossom/glow.json so Blossom Control can toggle it, dial each
corner's intensity, and pick each corner's colour (presets + custom). When the
glow is disabled a fully-transparent image is written, so the panel CSS can keep
referencing the same file unconditionally.

Run:  python3 tools/blossom-glow.py
"""

import json
import os

from PIL import Image
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "cinnamon", "common-assets", "panel", "blossom-corner-glow.png")
CFG = os.path.expanduser("~/.local/share/blossom/glow.json")

# corner key -> (x_frac, y_frac)
CORNERS = {"tl": (0.0, 0.0), "tr": (1.0, 0.0), "bl": (0.0, 1.0), "br": (1.0, 1.0)}

DEFAULT = {
    "enabled": True,
    "corners": {
        "tl": {"color": "#ff5aa8", "intensity": 0.85},  # pink   (warm left)
        "bl": {"color": "#ffc846", "intensity": 0.85},  # gold
        "tr": {"color": "#3cc8ff", "intensity": 0.85},  # blue   (cool right)
        "br": {"color": "#9669f2", "intensity": 0.85},  # violet
    },
}


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT))  # deep copy
    if os.path.exists(CFG):
        try:
            user = json.load(open(CFG))
            cfg["enabled"] = user.get("enabled", cfg["enabled"])
            for k, v in user.get("corners", {}).items():
                cfg["corners"].setdefault(k, {}).update(v)
        except (ValueError, OSError):
            pass
    return cfg


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def panel_size():
    """Bottom-panel width (= primary monitor width) and height, with fallbacks."""
    w, h = 2560, 40
    try:
        import gi
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk
        disp = Gdk.Display.get_default()
        mon = disp.get_primary_monitor() or disp.get_monitor(0)
        w = mon.get_geometry().width
    except Exception:
        pass
    try:
        import subprocess
        out = subprocess.run(["gsettings", "get", "org.cinnamon", "panels-height"],
                             capture_output=True, text=True).stdout
        # e.g. ['1:40', '2:60'] -> first panel height
        import re
        m = re.search(r"1:(\d+)", out)
        if m:
            h = int(m.group(1))
    except Exception:
        pass
    return w, h


def generate(cfg=None, out=OUT, size=None):
    cfg = cfg or load_cfg()
    W, H = size or panel_size()
    img = np.zeros((H, W, 4), dtype=float)
    if cfg.get("enabled", True):
        ys, xs = np.mgrid[0:H, 0:W]
        radius = max(180.0, W * 0.1)
        for key, (fx, fy) in CORNERS.items():
            c = cfg["corners"].get(key)
            if not c:
                continue
            inten = float(c.get("intensity", 0.0))
            if inten <= 0:
                continue
            r, g, b = hex_rgb(c.get("color", "#000000"))
            cx, cy = fx * W, fy * H
            d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
            a = np.clip(1 - d / radius, 0, 1) ** 1.6 * inten
            keep = 1 - img[..., 3]
            img[..., 0] += r * a * keep
            img[..., 1] += g * a * keep
            img[..., 2] += b * a * keep
            img[..., 3] += a * keep
    out_arr = np.zeros((H, W, 4), dtype="uint8")
    for i in range(3):
        out_arr[..., i] = np.clip(img[..., i], 0, 255)
    out_arr[..., 3] = np.clip(img[..., 3] * 255, 0, 255)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(out_arr, "RGBA").save(out)
    return out


if __name__ == "__main__":
    path = generate()
    print(f"wrote {path}")
