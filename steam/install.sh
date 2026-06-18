#!/usr/bin/env bash
# install.sh — apply the Blossom Steam skin.
#
#   (default)     NATIVE, no sudo. Builds the Rust `blossom-steam` binary, turns
#                 on Steam's CEF debugger, paints every window now, and adds a
#                 login autostart so it re-applies forever. Steam wipes any CSS
#                 written into its files on launch, so the skin is injected at
#                 runtime over the debugger instead — no Millennium, no root.
#
#   --millennium  Install as a Millennium theme (theme.json + the CSS). Cleaner
#                 (no debug port, no daemon) but Millennium itself needs a
#                 one-time sudo install — see the README.
#
#   --uninstall   Stop the daemon, remove autostart, drop the debug marker.
set -uo pipefail

SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
BIN="$SRC/blossom-steam/target/release/blossom-steam"
AUTOSTART="$HOME/.config/autostart/blossom-steam.desktop"
STEAM_ROOT="${STEAM_ROOT:-$HOME/.steam/steam}"
SUI="$STEAM_ROOT/steamui"
MARKER="$STEAM_ROOT/.cef-enable-remote-debugging"

PINK=$'\e[38;2;219;55;118m'; GOLD=$'\e[38;2;241;191;64m'; GREEN=$'\e[38;2;82;164;98m'; R=$'\e[0m'
ok()  { printf '  %s✓%s %s\n' "$GREEN" "$R" "$*"; }
hdr() { printf '\n%s❀ %s%s\n' "$PINK" "$*" "$R"; }
warn(){ printf '  %s!%s %s\n' "$GOLD" "$R" "$*"; }

# This is a user-level install — under sudo $HOME becomes /root and nothing is
# found. Bail early with a clear message instead of failing confusingly.
if [ "$(id -u)" = 0 ] && [ -n "${SUDO_USER:-}" ]; then
  printf '%s❀%s Run this WITHOUT sudo — it is a per-user install (sudo makes $HOME=/root).\n' "$PINK" "$R"
  exit 1
fi

millennium_installed() { [ -d /usr/lib/millennium ] || [ -e "$STEAM_ROOT/ubuntu12_64/libmillennium_hhx64.so" ]; }

build() {
  command -v cargo >/dev/null || { warn "Rust/cargo not found — get it at https://rustup.rs"; exit 1; }
  ( cd "$SRC/blossom-steam" && cargo build --release >/dev/null ) && ok "built blossom-steam ($(du -h "$BIN" | cut -f1))"
}

debugger_up() { curl -fsS -m2 http://localhost:8080/json/version >/dev/null 2>&1; }

native_install() {
  hdr "Installing Blossom for Steam (native · no sudo)"
  build
  if debugger_up; then ok "Steam CEF debugger already up"; else "$BIN" enable; fi
  mkdir -p "$(dirname "$AUTOSTART")"
  cat > "$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=Blossom Steam
Comment=Paint the Steam client in Blossom (AMOLED pink/gold)
Exec=$BIN live
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF
  ok "login autostart -> $AUTOSTART"
  pkill -f "$BIN live" 2>/dev/null || true
  setsid "$BIN" live >/dev/null 2>&1 < /dev/null & disown 2>/dev/null || true
  ok "Blossom is live — every Steam window, now and at every login"
  warn "This keeps a localhost-only debug port (8080) open while Steam runs."
  warn "After a Steam *client* update, run:  $BIN gen   (refresh the colour remap)"
}

native_uninstall() {
  hdr "Uninstalling Blossom for Steam"
  pkill -f "$BIN live" 2>/dev/null && ok "stopped the live daemon" || true
  rm -f "$AUTOSTART" && ok "removed autostart"
  rm -f "$MARKER"    && ok "removed the CEF debug marker (restart Steam to close port 8080)"
  warn "Restart Steam to drop the theme."
}

millennium_install() {
  hdr "Installing Blossom as a Millennium theme"
  [ -d "$SUI" ] || { warn "steamui not found at $SUI — set STEAM_ROOT"; exit 1; }
  mkdir -p "$SUI/skins"
  ln -sfn "$SRC" "$SUI/skins/Blossom" && ok "linked theme -> $SUI/skins/Blossom"
  if millennium_installed; then
    ok "Millennium detected"
    warn "Enable 'Blossom' in Steam → Millennium → Themes, then reload."
  else
    warn "Millennium is NOT installed yet. Install it once (this patches Steam; needs sudo):"
    printf '      curl -fsSL https://raw.githubusercontent.com/SteamClientHomebrew/Millennium/main/scripts/install.sh | sh\n'
    warn "Then re-run this, and enable 'Blossom' in Steam → Millennium → Themes."
  fi
}

case "${1:-}" in
  ""|install)     native_install ;;
  --millennium)   millennium_install ;;
  -u|--uninstall) native_uninstall ;;
  *) echo "usage: $0 [install|--millennium|--uninstall]"; exit 1 ;;
esac
