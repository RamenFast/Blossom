#!/bin/bash
# Pin Blossom onto the Cinnamon panel: recolour the menu-applet logo and
# install a launcher for Blossom Control. Idempotent — safe to re-run.
set -e

# menu applet → Blossom logo (the per-applet setting wins over the global one)
python3 - <<'PY'
import json, glob, os
for f in glob.glob(os.path.expanduser(
        "~/.config/cinnamon/spices/menu@cinnamon.org/*.json")):
    d = json.load(open(f)); d["menu-icon"]["value"] = "blossom-logo"
    json.dump(d, open(f, "w"), indent=4)
PY

# launcher for the control app (flower icon)
cat > ~/.local/share/applications/blossom-control.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Blossom Control
Exec=python3 $HOME/.themes/Blossom/tools/blossom-control.py
Icon=blossom-flower
Terminal=false
StartupWMClass=blossom-control
Categories=Settings;Utility;
EOF

echo "panel setup done — pin the flower via right-click panel → Add applets →"
echo "Panel launchers (or drag the menu entry onto the panel); Ctrl+Alt+Esc repaints"
