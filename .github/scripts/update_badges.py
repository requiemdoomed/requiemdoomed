#!/usr/bin/env python3
"""Builds the top-language and star badges for every project listed in README.md.

Runs inside GitHub Actions with the repo's own GITHUB_TOKEN, so it never hits the
anonymous rate limits that make shields.io badges slow or show "error fetching data".
Writes static SVGs to badges/, which README.md loads straight from this repo.
No third-party packages needed.
"""
import json, os, re, sys, urllib.request
from xml.sax.saxutils import escape

OWNER = os.environ.get("BADGE_OWNER", "requiemdoomed")
README = "README.md"
OUT = "badges"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

WIDTHS = {' ': 3.5, '!': 4.41, '"': 5.06, '#': 9.22, '$': 7.0, '%': 10.45, '&': 8.58, "'": 3.03, '(': 4.3, ')': 4.3, '*': 5.5, '+': 9.22, ',': 3.5, '-': 3.97, '.': 3.5, '/': 3.7, '0': 7.0, '1': 7.0, '2': 7.0, '3': 7.0, '4': 7.0, '5': 7.0, '6': 7.0, '7': 7.0, '8': 7.0, '9': 7.0, ':': 3.7, ';': 3.7, '<': 9.22, '=': 9.22, '>': 9.22, '?': 5.84, '@': 11.0, 'A': 7.53, 'B': 7.55, 'C': 7.69, 'D': 8.47, 'E': 6.95, 'F': 6.33, 'G': 8.53, 'H': 8.27, 'I': 3.25, 'J': 3.25, 'K': 7.22, 'L': 6.12, 'M': 9.48, 'N': 8.23, 'O': 8.66, 'P': 6.64, 'Q': 8.66, 'R': 7.64, 'S': 6.98, 'T': 6.72, 'U': 8.05, 'V': 7.53, 'W': 10.88, 'X': 7.53, 'Y': 6.72, 'Z': 7.53, '[': 4.3, '\\': 3.7, ']': 4.3, '^': 9.22, '_': 5.5, '`': 5.5, 'a': 6.73, 'b': 6.98, 'c': 6.05, 'd': 6.98, 'e': 6.77, 'f': 3.88, 'g': 6.98, 'h': 6.97, 'i': 3.06, 'j': 3.06, 'k': 6.38, 'l': 3.06, 'm': 10.72, 'n': 6.97, 'o': 6.73, 'p': 6.98, 'q': 6.98, 'r': 4.52, 's': 5.73, 't': 4.31, 'u': 6.97, 'v': 6.52, 'w': 9.0, 'x': 6.52, 'y': 6.52, 'z': 5.78, '{': 7.0, '|': 3.7, '}': 7.0, '~': 9.22}
def text_width(s):
    return sum(WIDTHS.get(ch, 13.0) for ch in s)

GREY, BLUE, LIGHTGREY = "#555", "#007ec6", "#9f9f9f"

def badge(label, message, label_color, message_color, title):
    """Flat badge drawn to match shields.io's 'flat' style."""
    lw = round(text_width(label) + 10)
    mw = round(text_width(message) + 10)
    w = lw + mw
    l, m = escape(label), escape(message)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="{escape(title)}">'
        f'<title>{escape(title)}</title>'
        '<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
        f'<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>'
        f'<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="{label_color}"/><rect x="{lw}" width="{mw}" height="20" fill="{message_color}"/><rect width="{w}" height="20" fill="url(#s)"/></g>'
        '<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{lw/2:.1f}" y="15" fill="#010101" fill-opacity=".3">{l}</text><text x="{lw/2:.1f}" y="14">{l}</text>'
        f'<text x="{lw+mw/2:.1f}" y="15" fill="#010101" fill-opacity=".3">{m}</text><text x="{lw+mw/2:.1f}" y="14">{m}</text>'
        '</g></svg>'
    )

def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "readme-badges"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def short(n):
    for div, suf in ((1_000_000, "M"), (1_000, "k")):
        if n >= div:
            v = n / div
            return (f"{v:.1f}".rstrip("0").rstrip(".")) + suf
    return str(n)

def repos_in_readme():
    text = open(README, encoding="utf-8").read()
    names = re.findall(r"badges/([A-Za-z0-9_.\-]+?)-(?:lang|stars)\.svg", text)
    names += re.findall(rf"img\.shields\.io/github/(?:stars|languages/top)/{OWNER}/([A-Za-z0-9_.\-]+)", text)
    return sorted(set(names))

def main():
    os.makedirs(OUT, exist_ok=True)
    repos = repos_in_readme()
    if not repos:
        sys.exit("No project badges found in README.md")
    failed = []
    for name in repos:
        try:
            info = api(f"/repos/{OWNER}/{name}")
            langs = api(f"/repos/{OWNER}/{name}/languages")
        except Exception as e:  # keep the last good badge if GitHub hiccups
            print(f"skip {name}: {e}")
            failed.append(name)
            continue
        stars = info.get("stargazers_count", 0)
        star_svg = badge("⭐", short(stars), GREY, GREY, f"⭐: {stars}")
        total = sum(langs.values())
        if total:
            top, size = max(langs.items(), key=lambda kv: kv[1])
            pct = f"{size / total * 100:.1f}%"
            lang_svg = badge(top.lower(), pct, GREY, BLUE, f"{top}: {pct}")
        else:
            lang_svg = badge("language", "none", GREY, LIGHTGREY, "language: none")
        for suffix, svg in (("stars", star_svg), ("lang", lang_svg)):
            path = f"{OUT}/{name}-{suffix}.svg"
            old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if old != svg:
                open(path, "w", encoding="utf-8").write(svg)
        print(f"{name}: {stars} stars, top language {langs and max(langs, key=langs.get) or 'none'}")
    if failed and len(failed) == len(repos):
        sys.exit("GitHub API unreachable; kept existing badges")

if __name__ == "__main__":
    main()
