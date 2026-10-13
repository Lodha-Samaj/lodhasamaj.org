#!/usr/bin/env python3
"""Report href/src targets inside the site that have no file behind them."""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ATTR = re.compile(r'''(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''', re.I)
SKIP = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#", "//")
# Script and style bodies and HTML comments are not markup. Blank their contents
# but keep the opening and closing tags of script/style, so a <script src> is still checked.
NON_MARKUP = re.compile(
    r'(<script\b[^>]*>).*?(</script\s*>)|(<style\b[^>]*>).*?(</style\s*>)|<!--.*?-->',
    re.I | re.S)


def _strip_non_markup(html: str) -> str:
    return NON_MARKUP.sub(lambda m: "".join(g for g in m.groups() if g), html)


def find_broken(root: str) -> list[str]:
    base = Path(root).resolve()
    broken: list[str] = []
    # Same guard as set_domain.is_site_file: a dot-directory (.git, .github,
    # .claude -- which can hold a worktree with a full second copy of the site)
    # is not part of the published site. Kept in step by a test in
    # tools/test_set_domain.py.
    for page in sorted(q for q in base.rglob("*.html")
                       if not any(part.startswith(".") or part == "node_modules"
                                  for part in q.relative_to(base).parts)):
        for match in ATTR.finditer(_strip_non_markup(page.read_text(encoding="utf-8", errors="replace"))):
            raw = next(g for g in match.groups() if g is not None)
            target = raw.strip()
            if not target or target.lower().startswith(SKIP):
                continue
            path = unquote(urlparse(target).path)
            if not path:
                continue
            resolved = (base / path.lstrip("/")) if path.startswith("/") \
                else (page.parent / path)
            if resolved.is_dir():
                resolved = resolved / "index.html"
            if not resolved.exists():
                broken.append(f"{page.relative_to(base)} -> {target}")
    return broken


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent.parent)
    broken = find_broken(root)
    for item in broken:
        print(item)
    print(f"\n{len(broken)} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
