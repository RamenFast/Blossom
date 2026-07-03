#!/usr/bin/env python3
"""gen-store.py — regenerate store.css, the Blossom remap for Steam's WEB pages.

The client UI is handled by webkit.css + generated.css (via `blossom-steam`).
But the store/community pages the client embeds pull their CSS from the
steamstatic CDN — cross-origin, no CORS — so the in-page extractor can never
read those rules. This script does the same job offline: download the CSS the
store/community front pages reference, keep every rule that paints a Steam
blue or a structural slate grey, and re-emit it in the Blossom palette.

Class names on the web store (.btnv6_*, #store_nav_area, …) have been stable
for years; re-run only if store accents visibly revert to blue:

    python3 gen-store.py          # rewrites store.css next to this script
"""
import gzip
import re
import sys
import urllib.request
from pathlib import Path

PAGES = [
    "https://store.steampowered.com/",
    "https://store.steampowered.com/app/570/",          # a game page
    "https://store.steampowered.com/search/?term=a",
    "https://steamcommunity.com/",
]

# ---- the Blossom mapping -----------------------------------------------------
# pink = what you're acting on · gold = reference · red = danger · greys -> void
HEX = {  # lowercase, no '#'
    # accent blues -> pink
    "1a9fff": "db3776", "1999ff": "db3776",
    "67c1f5": "e85a92", "66c0f4": "e85a92", "54a5d4": "e85a92",
    "a4d7f5": "f09bbd",
    "06bfff": "e85a92", "47bfff": "e85a92",
    "2b74ff": "b02a5e", "1a44c2": "8e2148",
    "3d6c8d": "8e2148", "2e5470": "6b1a38",
    # structural slate greys -> the void ramp (bg/border-ish props only)
    "3d4450": "1c1c1c", "0e141b": "000000", "171d25": "0a0a0a",
    "1b2838": "000000", "2a475e": "141414", "16202d": "0a0a0a",
    "23262e": "101010", "383a41": "1f1f1f", "464d58": "262626",
}
GREYS = {"3d4450", "0e141b", "171d25", "1b2838", "2a475e", "16202d",
         "23262e", "383a41", "464d58"}
# 417a9b is BOTH the muted-blue meta text AND the dark end of button gradients:
# as text it should recede (secondary light-blue), as paint it should stay pink.
DUAL = {"417a9b": {"color_like": "9fb3c2", "paint": "b02a5e"}}
GREY_OK = re.compile(r"^(background|border|box-shadow|outline|fill|stroke|--)")
COLOR_LIKE = re.compile(r"^(color|-webkit-text-fill-color)$")


def _hex_to_triplet(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _sub_hex(value, src, dst):
    return re.sub("#" + src, "#" + dst, value, flags=re.I)


def _sub_rgb(value, src, dst):
    s, d = _hex_to_triplet(src), _hex_to_triplet(dst)
    pat = r"\b{},\s*{},\s*{}\b".format(*s)
    return re.sub(pat, "{}, {}, {}".format(*d), value)


def _hits(value, h):
    if re.search("#" + h, value, re.I):
        return True
    return re.search(r"\b{},\s*{},\s*{}\b".format(*_hex_to_triplet(h)), value) is not None


def remap_decl(prop, value):
    """Return the remapped value if this declaration needs re-emitting, else None."""
    p = prop.strip().lower()
    hit = False
    for h, out in HEX.items():
        if not _hits(value, h):
            continue
        if h in GREYS and not GREY_OK.match(p):
            continue
        value = _sub_hex(value, h, out)
        value = _sub_rgb(value, h, out)
        hit = True
    for h, outs in DUAL.items():
        if _hits(value, h):
            out = outs["color_like"] if COLOR_LIKE.match(p) else outs["paint"]
            value = _sub_hex(value, h, out)
            value = _sub_rgb(value, h, out)
            hit = True
    return value if hit else None


# ---- a tiny CSS walker (brace/quote/paren aware — enough for minified CSS) ----
def rules(css, prefix=""):
    """Yield (at_prefix, selector, declarations) for every style rule."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            return
        head = css[i:j].strip()
        body, k = _read_block(css, j + 1)
        if head.startswith("@") and head.split("(")[0].split()[0] in (
                "@media", "@supports"):
            yield from rules(body, prefix + head + "{")
        elif head.startswith("@"):
            pass  # @font-face / @keyframes / @import blocks — no colours we chase
        else:
            yield prefix, head, body
        i = k


def _read_block(css, i):
    """Read a balanced {...} body starting after the '{'. Returns (body, index_after)."""
    depth, start, n = 1, i, len(css)
    while i < n:
        c = css[i]
        if c in "\"'":
            q = c
            i += 1
            while i < n and css[i] != q:
                i += 2 if css[i] == "\\" else 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return css[start:i], i + 1
        i += 1
    return css[start:], n


def split_decls(body):
    """Split 'a:b;c:d' respecting url(data:...;base64,...) parens."""
    out, cur, depth = [], [], 0
    for c in body:
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        if c == ";" and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur))
    return [d for d in (x.strip() for x in out) if ":" in d]


def remap_css(css):
    out = []
    for prefix, sel, body in rules(css):
        decls = []
        for d in split_decls(body):
            prop, _, val = d.partition(":")
            new = remap_decl(prop, val)
            if new is not None:
                decls.append(f"{prop.strip()}:{new.strip()} !important")
        if decls:
            rule = sel + "{" + ";".join(decls) + "}"
            out.append(rule + "}" * prefix.count("{") if not prefix
                       else prefix + rule + "}" * prefix.count("{"))
    return out


def fetch(url, timeout=20):
    """GET url; the steamstatic CDN gzips even unasked, so decompress if needed."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def css_urls(page_url):
    html = fetch(page_url, timeout=15)
    return re.findall(r'href="(https://[^"]+\.css[^"]*)"', html.replace("&amp;", "&"))


def main():
    seen_urls, seen_rules, sections, total = set(), set(), [], 0
    for page in PAGES:
        try:
            urls = css_urls(page)
        except Exception as e:
            print(f"  ! {page}: {e}", file=sys.stderr)
            continue
        for u in urls:
            key = u.split("?")[0]
            if key in seen_urls:
                continue
            seen_urls.add(key)
            try:
                css = fetch(u)
            except Exception as e:
                print(f"  ! {u}: {e}", file=sys.stderr)
                continue
            fresh = [r for r in remap_css(css) if r not in seen_rules]
            seen_rules.update(fresh)
            if fresh:
                sections.append(f"\n/* == {len(fresh)} rules from {key} == */\n"
                                + "\n".join(fresh))
                total += len(fresh)
                print(f"  ✓ {key.rsplit('/', 1)[-1]}: {len(fresh)} rules")
    out = Path(__file__).with_name("store.css")
    out.write_text(
        f"/* gen-store.py: {total} rules — the Blossom remap for Steam's web "
        "store/community CSS.\n   Regenerate with `python3 gen-store.py` if "
        "store accents revert to blue. */\n" + "\n".join(sections) + "\n")
    print(f"✓ wrote {out} ({total} rules)")


if __name__ == "__main__":
    main()
