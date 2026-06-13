#!/usr/bin/env bash
#
# Blossom xmonad installer — Linux Mint / Ubuntu / Debian.
# Installs xmonad + the bits the config uses, links the Blossom config into place,
# and registers a login session. Needs sudo for apt + the session file.
#
#   bash wm/install.sh
#
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Installing xmonad + tools (apt)…"
# A failing third-party repo (e.g. an expired Spotify key) must not abort us —
# apt still refreshed every other list, so just continue.
sudo apt update || echo "  (apt update reported a warning from some repo — continuing)"
sudo apt install -y \
  xmonad libghc-xmonad-dev libghc-xmonad-contrib-dev \
  xmobar suckless-tools picom feh x11-xserver-utils \
  gnome-screenshot

echo "==> Linking the Blossom config into ~/.config…"
mkdir -p ~/.config/xmonad ~/.config/xmobar
ln -sfn "$REPO/wm/xmonad/xmonad.hs" ~/.config/xmonad/xmonad.hs
ln -sfn "$REPO/wm/xmobar/xmobarrc"  ~/.config/xmobar/xmobarrc
# optional compositor config
cp -n "$REPO/wm/picom.conf" ~/.config/picom.conf 2>/dev/null || true

echo "==> Registering the login session…"
sudo install -Dm644 "$REPO/wm/blossom-xmonad.desktop" \
  /usr/share/xsessions/blossom-xmonad.desktop

echo "==> Compiling xmonad…"
xmonad --recompile

cat <<'DONE'

Done. ✿  Log out, choose "Blossom (xmonad)" from the session menu (the gear/cog
on the login screen), and log back in.

First keys to try:
  Super+Return  terminal        Super+d   app launcher (dmenu)
  Super+j / k   focus down/up   Super+h / l  shrink/grow master pane
  Super+Space   next layout     Super+f   fullscreen
  Super+1..9    workspaces      Super+S+1..9  send window to workspace
  Super+S+c     close window    Super+c   open Blossom Control
  Super+b       toggle the bar  Super+S+x  leave xmonad

Keep your Cinnamon login too — nothing here touches it; this is just a second
session you can hop into and out of. Full cheat-sheet: README "xmonad" section.
DONE
