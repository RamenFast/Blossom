#!/bin/bash
# Build the Blossom .deb + .rpm — the desktop theme + icon pack, installed
# system-wide (/usr/share/themes, /usr/share/icons). The extras (apps/, steam/,
# blob-emojis/, wm/, tools/) are user-level and stay repo-based.
#
# VERSION must match the release tag (version law: tag == filename == package).
set -euo pipefail

VERSION=1.0.0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/packaging/dist"
STAGE="$DIST/stage"

rm -rf "$DIST"
mkdir -p "$STAGE/usr/share/themes/Blossom" "$STAGE/usr/share/icons" \
         "$STAGE/usr/share/doc/blossom-theme"

# ---- payload (identical for deb and rpm) ---------------------------------
cp "$ROOT/index.theme" "$STAGE/usr/share/themes/Blossom/"
for d in cinnamon gtk-2.0 gtk-3.0 gtk-4.0 libadwaita-1.5 libadwaita-1.7 \
         metacity-1 xfwm4 openbox-3; do
    cp -r "$ROOT/$d" "$STAGE/usr/share/themes/Blossom/"
done
cp -r "$ROOT/icons/Blossom" "$STAGE/usr/share/icons/Blossom"
rm -f "$STAGE/usr/share/icons/Blossom/icon-theme.cache"   # postinst regenerates
find "$STAGE" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
cp "$ROOT/LICENSE" "$STAGE/usr/share/doc/blossom-theme/copyright"

# ---- deb ------------------------------------------------------------------
DEB="$DIST/deb"
cp -r "$STAGE" "$DEB"
mkdir -p "$DEB/DEBIAN"
cat > "$DEB/DEBIAN/control" <<EOF
Package: blossom-theme
Version: $VERSION
Section: x11
Priority: optional
Architecture: all
Recommends: papirus-icon-theme
Maintainer: Ben (RamenFast) <2bmillerb@gmail.com>
Homepage: https://github.com/RamenFast/Blossom
Description: AMOLED true-black desktop theme - pink primary, gold secondary
 Cinnamon shell + GTK 2/3/4 + libadwaita + window borders + icon pack,
 generated from one palette engine; importance reads through colour.
 The extras (Steam skin, blob emoji, per-app themes, xmonad session)
 live in the repo: https://github.com/RamenFast/Blossom
EOF
cat > "$DEB/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -q /usr/share/icons/Blossom || true
fi
EOF
chmod 755 "$DEB/DEBIAN/postinst"
dpkg-deb --build --root-owner-group "$DEB" \
    "$DIST/blossom-theme_${VERSION}_all.deb" >/dev/null

# ---- rpm ------------------------------------------------------------------
RPMTOP="$DIST/rpm"
mkdir -p "$RPMTOP"/{SPECS,BUILD,RPMS}
cat > "$RPMTOP/SPECS/blossom-theme.spec" <<EOF
Name:      blossom-theme
Version:   $VERSION
Release:   1
Summary:   AMOLED true-black desktop theme - pink primary, gold secondary
License:   GPL-3.0-or-later
URL:       https://github.com/RamenFast/Blossom
BuildArch: noarch
Recommends: papirus-icon-theme

%description
Cinnamon shell + GTK 2/3/4 + libadwaita + window borders + icon pack,
generated from one palette engine; importance reads through colour.
The extras (Steam skin, blob emoji, per-app themes, xmonad session)
live in the repo: https://github.com/RamenFast/Blossom

%install
cp -r $STAGE/* %{buildroot}/

%post
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -q /usr/share/icons/Blossom || :
fi

%files
/usr/share/themes/Blossom
/usr/share/icons/Blossom
%doc /usr/share/doc/blossom-theme/copyright
EOF
rpmbuild --define "_topdir $RPMTOP" -bb "$RPMTOP/SPECS/blossom-theme.spec" \
    --quiet 2>/dev/null
cp "$RPMTOP/RPMS/noarch/blossom-theme-${VERSION}-1.noarch.rpm" "$DIST/"

echo "built:"
ls -sh1 "$DIST" | grep -E '\.(deb|rpm)$'
