#!/usr/bin/env bash
# Blossom · blob-emojis — install Blobmoji as the desktop-wide emoji font.
#
#   ./install.sh              install / refresh (user level + every installed flatpak)
#   ./install.sh --system     additionally install for all users (uses sudo)
#   ./install.sh --uninstall  remove what this script installed (add --system for system copies)
#
# Idempotent — re-run any time, e.g. right after installing a new flatpak so
# that app gets the emoji config too. Running apps keep their old emoji font
# until they restart; nothing is killed by this script.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FONT_SRC="$SCRIPT_DIR/Blobmoji.ttf"
CONF_SRC="$SCRIPT_DIR/75-blobmoji.conf"

FONT_DST="$HOME/.local/share/fonts/blossom/Blobmoji.ttf"
CONF_DST="$HOME/.config/fontconfig/conf.d/75-blobmoji.conf"

SYS_FONT_DST="/usr/local/share/fonts/blossom/Blobmoji.ttf"
SYS_CONF_DST="/etc/fonts/conf.d/75-blobmoji.conf"

MODE="install" SYSTEM=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) MODE="uninstall" ;;
    --system)    SYSTEM=1 ;;
    -h|--help)   sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg (try --help)" >&2; exit 2 ;;
  esac
done

# Flatpak sandboxes never read ~/.config/fontconfig — each app reads its own
# XDG_CONFIG_HOME at ~/.var/app/<id>/config. Host user fonts are auto-mounted
# at /run/host/user-fonts, so only the conf needs a per-app copy.
flatpak_conf_paths() {
  command -v flatpak >/dev/null 2>&1 || return 0
  flatpak list --app --columns=application 2>/dev/null | while read -r id; do
    [ -n "$id" ] && echo "$HOME/.var/app/$id/config/fontconfig/conf.d/75-blobmoji.conf"
  done
}

if [ "$MODE" = "install" ]; then
  [ -f "$FONT_SRC" ] || { echo "missing $FONT_SRC — restore it with:
  curl -L -o '$FONT_SRC' https://github.com/C1710/blobmoji/releases/download/v15.0/Blobmoji.ttf" >&2; exit 1; }

  install -Dm644 "$FONT_SRC" "$FONT_DST";  echo "font → $FONT_DST"
  install -Dm644 "$CONF_SRC" "$CONF_DST";  echo "conf → $CONF_DST"
  while read -r p; do
    [ -n "$p" ] || continue
    install -Dm644 "$CONF_SRC" "$p";       echo "conf → $p"
  done < <(flatpak_conf_paths)

  if [ "$SYSTEM" = 1 ]; then
    sudo install -Dm644 "$FONT_SRC" "$SYS_FONT_DST"
    sudo install -Dm644 "$CONF_SRC" "$SYS_CONF_DST"
    sudo fc-cache -f --system-only >/dev/null || true
    echo "system copies → $SYS_FONT_DST, $SYS_CONF_DST"
  fi

  fc-cache -f >/dev/null

  echo
  resolved="$(fc-match emoji)"
  echo "fc-match emoji                      → $resolved"
  echo "fc-match 'sans-serif:lang=und-zsye' → $(fc-match 'sans-serif:lang=und-zsye')"
  case "$resolved" in
    Blobmoji*) echo "OK — emoji resolve to Blobmoji. New app launches get blobs;"
               echo "already-running apps keep old emoji until restarted"
               echo "(Cinnamon shell itself: Ctrl+Alt+Esc restarts it in place)." ;;
    *) echo "PROBLEM — emoji still resolve elsewhere. Check $CONF_DST" >&2; exit 1 ;;
  esac
else
  rm -f "$FONT_DST" "$CONF_DST"
  rmdir --ignore-fail-on-non-empty "$(dirname "$FONT_DST")" 2>/dev/null || true
  while read -r p; do [ -n "$p" ] && rm -f "$p"; done < <(flatpak_conf_paths)
  if [ "$SYSTEM" = 1 ]; then
    sudo rm -f "$SYS_FONT_DST" "$SYS_CONF_DST"
    sudo fc-cache -f --system-only >/dev/null || true
  fi
  fc-cache -f >/dev/null
  echo "Blobmoji removed — emoji fall back to Noto Color Emoji (restart apps to see it)."
fi
