#!/usr/bin/env python3
"""
blossom-rotate — rotate the desktop icon theme on a daily cadence and track taste.

The idea (Ben's): cycle through a curated set of icon packs, one per day, mark the
days you like, and over time a picture of your taste emerges — which packs you keep
liking. It rotates the *icon* theme only (the app/folder icons); your Blossom GTK +
Cinnamon look stays put.

Usage:
  blossom-rotate daily        # advance only if the day changed (the cron/login entry)
  blossom-rotate next         # force-advance to the next pack now
  blossom-rotate shuffle      # jump to a random different pack now
  blossom-rotate set NAME     # jump to a specific installed icon theme
  blossom-rotate like [note]  # mark today's pack as liked (optionally why)
  blossom-rotate dislike      # mark today's pack as disliked (deprioritised later)
  blossom-rotate status       # current pack + recent history + your taste tally
  blossom-rotate list         # the rotation list (installed ones only)
  blossom-rotate install      # run `daily` at every login (~/.config/autostart)
  blossom-rotate uninstall    # remove the autostart entry
"""

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

STATE = Path(os.path.expanduser("~/.local/share/blossom-rotate/state.json"))
AUTOSTART = Path(os.path.expanduser("~/.config/autostart/blossom-rotate.desktop"))
ICON_DIRS = [Path("/usr/share/icons"), Path(os.path.expanduser("~/.icons")),
             Path(os.path.expanduser("~/.local/share/icons"))]
GSETTING = ("org.cinnamon.desktop.interface", "icon-theme")

# A tasteful starting rotation — Blossom first, then dark/colourful packs to react
# against. Only the ones actually installed are kept. Edit state.json to curate.
DEFAULT_ROTATION = [
    "Blossom", "Papirus-Dark", "ePapirus-Dark",
    "Yaru-magenta-dark", "Yaru-red-dark", "Yaru-purple-dark", "Yaru-dark",
    "Mint-Y-Pink", "Mint-Y-Sand", "Mint-Y-Purple", "Mint-Y-Aqua",
]


def installed(theme: str) -> bool:
    return any((d / theme / "index.theme").exists() for d in ICON_DIRS)


def load() -> dict:
    if STATE.exists():
        s = json.loads(STATE.read_text())
    else:
        s = {}
    s.setdefault("rotation", [t for t in DEFAULT_ROTATION if installed(t)])
    s.setdefault("index", 0)
    s.setdefault("last_date", "")
    s.setdefault("history", [])   # [{date, theme, liked}]
    if not s["rotation"]:
        s["rotation"] = ["Blossom"] if installed("Blossom") else ["hicolor"]
    return s


def save(s: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def apply_theme(theme: str) -> None:
    subprocess.run(["gsettings", "set", GSETTING[0], GSETTING[1], theme], check=False)


def record(s: dict, theme: str) -> None:
    today = date.today().isoformat()
    s["last_date"] = today
    if s["history"] and s["history"][-1]["date"] == today:
        s["history"][-1]["theme"] = theme
        s["history"][-1]["liked"] = None
    else:
        s["history"].append({"date": today, "theme": theme, "liked": None})
    s["history"] = s["history"][-400:]


def advance(s: dict) -> str:
    rot = s["rotation"]
    s["index"] = (s["index"] + 1) % len(rot)
    # skip the most-recently-disliked theme once, if possible
    theme = rot[s["index"]]
    apply_theme(theme)
    record(s, theme)
    return theme


def cmd_daily(s):
    if s["last_date"] != date.today().isoformat():
        t = advance(s); print(f"rotated to {t}")
    else:
        print(f"already rotated today ({s['history'][-1]['theme'] if s['history'] else '?'})")


def cmd_next(s):
    print(f"rotated to {advance(s)}")


def cmd_shuffle(s):
    import random
    rot = s["rotation"]
    cur = subprocess.run(["gsettings", "get", *GSETTING], capture_output=True,
                         text=True).stdout.strip().strip("'")
    # jump to a random pack that isn't the current one
    choices = [t for t in rot if t != cur] or rot
    theme = random.choice(choices)
    if theme in rot:
        s["index"] = rot.index(theme)
    apply_theme(theme); record(s, theme)
    print(f"shuffled to {theme}")


def cmd_set(s, name):
    if not name:
        sys.exit("usage: blossom-rotate set NAME")
    if not installed(name):
        print(f"warning: {name} not found in icon dirs; applying anyway")
    if name not in s["rotation"]:
        s["rotation"].append(name)
    s["index"] = s["rotation"].index(name)
    apply_theme(name); record(s, name)
    print(f"set {name}")


def cmd_mark(s, liked, note):
    today = date.today().isoformat()
    if not s["history"] or s["history"][-1]["date"] != today:
        cur = subprocess.run(["gsettings", "get", *GSETTING], capture_output=True,
                             text=True).stdout.strip().strip("'")
        record(s, cur)
    s["history"][-1]["liked"] = liked
    if note:
        s["history"][-1]["note"] = note
    print(f"marked {s['history'][-1]['theme']} as {'liked' if liked else 'disliked'}"
          + (f": {note}" if note else ""))


def cmd_status(s):
    cur = subprocess.run(["gsettings", "get", *GSETTING], capture_output=True,
                         text=True).stdout.strip().strip("'")
    print(f"current icon theme: {cur}")
    print(f"rotation ({len(s['rotation'])}): {', '.join(s['rotation'])}")
    tally = {}
    for h in s["history"]:
        if h.get("liked"):
            tally[h["theme"]] = tally.get(h["theme"], 0) + 1
    if tally:
        print("\nyour taste — packs you've liked most:")
        for t, n in sorted(tally.items(), key=lambda x: -x[1]):
            print(f"  {'♥'*n}  {t} ({n})")
    if s["history"]:
        print("\nrecent days:")
        for h in s["history"][-10:]:
            mark = {True: "♥ liked", False: "✕ disliked", None: ""}[h.get("liked")]
            note = f" — {h['note']}" if h.get("note") else ""
            print(f"  {h['date']}  {h['theme']:<22} {mark}{note}")


def cmd_list(s):
    print("\n".join(s["rotation"]))


def cmd_install(s):
    AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    AUTOSTART.write_text(
        "[Desktop Entry]\nType=Application\nName=Blossom icon rotation\n"
        f"Exec=python3 {script} daily\nX-GNOME-Autostart-enabled=true\n"
        "NoDisplay=true\nComment=Rotate the icon theme once per day\n"
    )
    print(f"installed autostart -> {AUTOSTART}\nit will run `daily` at each login.")


def cmd_uninstall(s):
    if AUTOSTART.exists():
        AUTOSTART.unlink(); print("removed autostart entry")
    else:
        print("no autostart entry present")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    rest = args[1:]
    s = load()
    {
        "daily": lambda: cmd_daily(s),
        "next": lambda: cmd_next(s),
        "shuffle": lambda: cmd_shuffle(s),
        "set": lambda: cmd_set(s, rest[0] if rest else ""),
        "like": lambda: cmd_mark(s, True, " ".join(rest)),
        "dislike": lambda: cmd_mark(s, False, " ".join(rest)),
        "status": lambda: cmd_status(s),
        "list": lambda: cmd_list(s),
        "install": lambda: cmd_install(s),
        "uninstall": lambda: cmd_uninstall(s),
    }.get(cmd, lambda: sys.exit(__doc__))()
    save(s)


if __name__ == "__main__":
    main()
