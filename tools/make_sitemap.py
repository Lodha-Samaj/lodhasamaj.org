#!/usr/bin/env python3
"""Generate sitemap.xml from the index.html files actually on disk.

Usage: python3 tools/make_sitemap.py DOMAIN [--root DIR]

Every page under hi/ and en/ is listed, with xhtml:link alternates pairing it
with its counterpart in the other language (only when that counterpart exists).
New donor years appear automatically. Normally run via tools/set_domain.py.
"""
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

LANGS = ("hi", "en")


def normalize_domain(domain: str) -> str:
    """Return 'https://host' or raise ValueError. Never guesses a domain."""
    d = domain.strip().rstrip("/")
    d = re.sub(r"^https://", "", d)
    if "REPLACE" in d.upper() or not re.fullmatch(
            r"[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+", d):
        raise ValueError(f"not a usable domain name: {domain!r} (give e.g. example.com, no path)")
    return "https://" + d.lower()


def page_paths(root: Path) -> list[str]:
    """Root-relative URL paths like '/hi/daan/2025/' for every language page."""
    paths = []
    for lang in LANGS:
        for f in sorted((root / lang).rglob("index.html")):
            rel = f.parent.relative_to(root).as_posix()
            paths.append("/" + rel + "/")
    return paths


def counterpart(path: str) -> str:
    return "/" + ("en" if path.startswith("/hi/") else "hi") + path[3:]


def build(root: Path, base: str) -> str:
    paths = page_paths(root)
    existing = set(paths)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for p in paths:
        out.append("  <url>")
        out.append(f"    <loc>{escape(base + p)}</loc>")
        other = counterpart(p)
        if other in existing:
            hi, en = (p, other) if p.startswith("/hi/") else (other, p)
            for code, target in (("hi", hi), ("en", en), ("x-default", hi)):
                out.append(f'    <xhtml:link rel="alternate" hreflang="{code}" '
                           f'href="{escape(base + target)}"/>')
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def write(root: Path, domain: str) -> int:
    base = normalize_domain(domain)
    (root / "sitemap.xml").write_text(build(root, base), encoding="utf-8")
    return len(page_paths(root))


def main(argv: list[str]) -> int:
    args = argv[1:]
    root = Path(__file__).resolve().parent.parent
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        n = write(root, args[0])
    except ValueError as exc:
        print(f"error: {exc}")
        return 2
    print(f"sitemap.xml written with {n} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
