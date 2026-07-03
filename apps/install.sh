#!/usr/bin/env bash
# apps/install.sh — wire the Blossom app themes into their homes.
#
# Everything is a symlink back into this repo, so a `git pull` (or an edit)
# updates every app at once. Safe to re-run; each step is independent.
#
#   ./install.sh            install everything below
#   ./install.sh --list     show what would be linked where
set -uo pipefail

SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PINK=$'\e[38;2;219;55;118m'; GOLD=$'\e[38;2;241;191;64m'; GREEN=$'\e[38;2;82;164;98m'; R=$'\e[0m'
ok()  { printf '  %s✓%s %s\n' "$GREEN" "$R" "$*"; }
hdr() { printf '\n%s❀ %s%s\n' "$PINK" "$*" "$R"; }
warn(){ printf '  %s!%s %s\n' "$GOLD" "$R" "$*"; }

link() { # link <repo-file> <dest>
  mkdir -p "$(dirname "$2")" && ln -sfn "$SRC/$1" "$2" && ok "$1 -> $2"
}

if [ "${1:-}" = "--list" ]; then
  sed -n 's/^  link "\([^"]*\)" "\([^"]*\)".*/  \1 -> \2/p' "$0"; exit 0
fi

hdr "Terminals"
link "kitty/blossom.conf" "$HOME/.config/kitty/themes/blossom.conf"
grep -q "themes/blossom.conf" "$HOME/.config/kitty/kitty.conf" 2>/dev/null \
  || warn "kitty: add   include themes/blossom.conf   to kitty.conf"
link "ghostty/Blossom" "$HOME/.config/ghostty/themes/Blossom"
grep -q "^theme = Blossom" "$HOME/.config/ghostty/config" 2>/dev/null \
  || warn "ghostty: add   theme = Blossom   to the config"

hdr "btop"
link "btop/blossom.theme" "$HOME/.config/btop/themes/blossom.theme"
[ -f "$HOME/.config/btop/btop.conf" ] || printf 'color_theme = "blossom"\ntheme_background = True\ntruecolor = True\n' > "$HOME/.config/btop/btop.conf"
grep -q 'color_theme = "blossom"' "$HOME/.config/btop/btop.conf" \
  || warn 'btop: set   color_theme = "blossom"   in btop.conf'

hdr "Editors (GtkSourceView: xed, gedit, …)"
for v in gtksourceview-3.0 gtksourceview-4 gtksourceview-5; do
  link "gtksourceview/blossom.xml" "$HOME/.local/share/$v/styles/blossom.xml"
done
command -v gsettings >/dev/null && gsettings set org.x.editor.preferences.editor scheme 'blossom' 2>/dev/null \
  && ok "xed scheme -> blossom"

hdr "Qt (qt5ct/qt6ct — needs QT_QPA_PLATFORMTHEME=qt5ct in the session)"
link "qt/Blossom.conf" "$HOME/.config/qt5ct/colors/Blossom.conf"
link "qt/Blossom.conf" "$HOME/.config/qt6ct/colors/Blossom.conf"
command -v qt5ct >/dev/null || warn "qt5ct not installed:  sudo apt install qt5ct qt6ct"
grep -qs "QT_QPA_PLATFORMTHEME" "$HOME/.xsessionrc" \
  || warn 'add   export QT_QPA_PLATFORMTHEME=qt5ct   to ~/.xsessionrc (then re-login)'

hdr "Flatpak GTK apps"
if command -v flatpak >/dev/null; then
  for app in $(flatpak list --app --columns=application 2>/dev/null); do
    flatpak override --user --filesystem="$HOME/.themes:ro" "$app" 2>/dev/null
    flatpak override --user --filesystem="$HOME/.icons:ro"  "$app" 2>/dev/null
    flatpak override --user --env=GTK_THEME=Blossom "$app" 2>/dev/null
    flatpak override --user --env=ICON_THEME=Blossom "$app" 2>/dev/null
  done
  ok "flatpak overrides (GTK_THEME=Blossom + theme/icon access) for all apps"
fi

hdr "Obsidian"
OBS_JSON="$HOME/.config/obsidian/obsidian.json"
if [ -f "$OBS_JSON" ]; then
  python3 - "$OBS_JSON" "$SRC" <<'PY'
import json, os, sys
vaults = json.load(open(sys.argv[1])).get("vaults", {})
for v in vaults.values():
    snip = os.path.join(v["path"], ".obsidian", "snippets")
    os.makedirs(snip, exist_ok=True)
    dst = os.path.join(snip, "blossom.css")
    src = os.path.join(sys.argv[2], "obsidian", "blossom.css")
    if os.path.islink(dst) or os.path.exists(dst):
        os.remove(dst)
    os.symlink(src, dst)
    print(f"  \033[38;2;82;164;98m✓\033[0m obsidian snippet -> {dst}")
    print("    (enable it: Settings → Appearance → CSS snippets → blossom)")
PY
else
  warn "Obsidian not configured — skipped"
fi

hdr "Manual (client mods — your call)"
warn "Discord: install Vencord, then  ln -s $SRC/discord/blossom.theme.css ~/.config/Vencord/themes/"
warn "Spotify: install spicetify, then  ln -s $SRC/spotify/Blossom ~/.config/spicetify/Themes/Blossom"
warn "         && spicetify config current_theme Blossom && spicetify apply"
printf '\n%s❀ done%s\n' "$PINK" "$R"
