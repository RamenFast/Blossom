# Blossom app themes ❀

The Blossom look — AMOLED true-black, **pink** primary, **gold** secondary,
light-blue text — carried into the applications the desktop theme can't reach.
Same palette, same rule: **pink is what you're acting on, gold is the reference,
red is danger**; everything else recedes into the void.

```bash
./install.sh          # symlink every theme into place (safe to re-run)
./install.sh --list   # show what goes where
```

Everything installs as a **symlink back into this repo**, so edits and
`git pull` propagate everywhere at once.

| App | File | How it lands |
| --- | --- | --- |
| kitty | `kitty/blossom.conf` | `include themes/blossom.conf` in kitty.conf |
| ghostty | `ghostty/Blossom` | `theme = Blossom` in the config |
| btop | `btop/blossom.theme` | `color_theme = "blossom"` in btop.conf |
| xed / gedit / GtkSourceView | `gtksourceview/blossom.xml` | style scheme "Blossom", set via gsettings |
| Qt apps (VLC, corectrl, …) | `qt/Blossom.conf` | qt5ct/qt6ct palette (Fusion style), `QT_QPA_PLATFORMTHEME=qt5ct` |
| Flatpak GTK apps | *(overrides)* | `GTK_THEME=Blossom` + read access to `~/.themes`, `~/.icons` |
| Obsidian | `obsidian/blossom.css` | CSS snippet per vault (stable CSS variables) |
| Discord | `discord/blossom.theme.css` | needs Vencord — manual, see install.sh output |
| Spotify | `spotify/Blossom/color.ini` | needs spicetify — manual, see install.sh output |

The Steam client has its own, deeper treatment — see [`../steam/`](../steam/).

## ANSI terminal palette

Both terminal schemes share one 16-colour mapping, designed so semantics
survive: red stays *danger*, green stays *success*, yellow is the **gold**
reference, magenta is the **pink** accent, blue/cyan stay readable against
true black as members of the light-blue text family.

| slot | colour | | slot | colour |
| --- | --- | --- | --- | --- |
| 0 black | `#0a0a0a` | | 8 | `#3b3b3b` |
| 1 red | `#ec4e53` | | 9 | `#ff7078` |
| 2 green | `#52a462` | | 10 | `#74c584` |
| 3 yellow | `#f1bf40` | | 11 | `#ffd666` |
| 4 blue | `#5da3d6` | | 12 | `#8cc3ea` |
| 5 magenta | `#db3776` | | 13 | `#e85a92` |
| 6 cyan | `#6fc3c9` | | 14 | `#98dde2` |
| 7 white | `#9fb3c2` | | 15 | `#eaf6ff` |

Background `#000000`, foreground `#eaf6ff`, cursor + selection pink `#db3776`.
