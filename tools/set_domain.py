#!/usr/bin/env python3
"""Make the site's URLs absolute once the domain is chosen (the "sweep").

Usage:
  python3 tools/set_domain.py DOMAIN [--root DIR]          rewrite pages, robots.txt, sitemap.xml
  python3 tools/set_domain.py DOMAIN --force [--root DIR]  re-sweep a site already swept (e.g. typo)
  python3 tools/set_domain.py --check [--root DIR]         publish gate

WHY: link-preview bots (WhatsApp, Facebook) and search engines ignore
root-relative canonical / hreflang / og:url / og:image. Until this runs, a
WhatsApp share of the site shows no preview image.

A site that was already swept is REFUSED unless --force is given, so a second
run with a different domain can never leave a half-and-half site.
Undo a sweep you have not committed with:  git checkout -- .

--check fails unless every page carries all required head tags, every URL in
them is absolute https, and pages, robots.txt and sitemap.xml share ONE host.
It also refuses while a placeholder is still live (the example.org email, a
REPLACE-WITH-DOMAIN) or data/events.json still says "needsConfirmation": true,
so every publish-blocker is enforced by this one gate.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from make_sitemap import normalize_domain, write as write_sitemap

PLACEHOLDER = "REPLACE-WITH-DOMAIN"
COMMENT = re.compile(r"<!--.*?-->", re.S)
TAG = re.compile(r"<(link|meta)\b[^>]*>", re.I)
ATTR = re.compile(r'([A-Za-z][\w:-]*)\s*=\s*"([^"]*)"')
HOST = re.compile(r"https://([^/\s\"'<>]+)")


def head_tags(html: str):
    """Yield (key, url_attr, tag_text, attrs) for the URL-bearing head tags.

    key is canonical | hreflang:<code> | og:url | og:image. Attribute order is
    irrelevant."""
    for m in TAG.finditer(COMMENT.sub("", html)):
        attrs = dict(ATTR.findall(m.group(0)))
        if m.group(1).lower() == "link" and attrs.get("rel") == "canonical" and "href" in attrs:
            yield "canonical", "href", attrs
        elif m.group(1).lower() == "link" and attrs.get("rel") == "alternate" \
                and "hreflang" in attrs and "href" in attrs:
            yield "hreflang:" + attrs["hreflang"], "href", attrs
        elif m.group(1).lower() == "meta" and attrs.get("property") in ("og:url", "og:image") \
                and "content" in attrs:
            yield attrs["property"], "content", attrs


def required_keys(root: Path, page: Path) -> set[str]:
    if page.parent == root:          # root index.html is only a redirect page
        return {"canonical"}
    return {"canonical", "hreflang:hi", "hreflang:en", "hreflang:x-default", "og:url", "og:image"}


def is_site_file(root: Path, p: Path) -> bool:
    """Is this file part of the published site?

    Anything inside a dot-directory is not: .git, .github, .claude (which can
    hold a git worktree containing a FULL SECOND COPY of every page), and any
    editor or tool cache. A served page never lives in one. Without this, a
    stray copy of the site next to the real one gets swept at launch and
    listed in the public sitemap -- publishing internal paths to search
    engines. check_links.py has the same guard; the two must stay in step
    and test_site_file_guard_matches_check_links pins that."""
    rel = p.relative_to(root).parts
    return not any(part.startswith(".") or part == "node_modules" for part in rel)


def pages(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.html") if is_site_file(root, p))


def sweep_html(html: str, base: str, force: bool = False) -> str:
    """Rewrite URL attributes of the head tags only (comments and body untouched)."""
    out, pos = [], 0
    clean = html
    for m in TAG.finditer(clean):
        if any(c.start() <= m.start() < c.end() for c in COMMENT.finditer(clean)):
            continue
        tag = m.group(0)
        found = list(head_tags(tag))
        if not found:
            continue
        _, attr, attrs = found[0]
        url = attrs[attr]
        if url.startswith("/") and not url.startswith("//"):
            new = base + url
        elif force and url.startswith("https://"):
            new = base + re.sub(r"^https://[^/]+", "", url)
        else:
            continue
        out.append(clean[pos:m.start()] + tag.replace(f'{attr}="{url}"', f'{attr}="{new}"', 1))
        pos = m.end()
    return "".join(out) + clean[pos:]


def hosts_in(root: Path) -> dict[str, set[str]]:
    """host -> files mentioning it, over head tags, robots.txt and sitemap.xml."""
    found: dict[str, set[str]] = {}
    for page in pages(root):
        for _, attr, attrs in head_tags(page.read_text(encoding="utf-8")):
            for h in HOST.findall(attrs[attr]):
                found.setdefault(h, set()).add(str(page.relative_to(root)))
    for name in ("robots.txt", "sitemap.xml"):
        f = root / name
        if f.exists():
            for h in HOST.findall(f.read_text(encoding="utf-8")):
                if h == PLACEHOLDER:
                    continue
                found.setdefault(h, set()).add(name)
    return found


PLACEHOLDERS = ("example.org", PLACEHOLDER)


def placeholder_problems(root: Path) -> list[str]:
    bad = []
    files = list(pages(root))
    nav = root / "assets" / "js" / "nav.js"
    if nav.exists():
        files.append(nav)
    for f in files:
        text = f.read_text(encoding="utf-8")
        if f.suffix == ".html":
            text = COMMENT.sub("", text)        # REVIEW comments may name them
        else:
            text = re.sub(r"(?m)^\s*//.*$", "", text)
        for needle in PLACEHOLDERS:
            if needle in text:
                bad.append(f"{f.relative_to(root)}: still contains the placeholder {needle}")
    events = root / "data" / "events.json"
    if events.exists():
        try:
            if json.loads(events.read_text(encoding="utf-8")).get("needsConfirmation") is True:
                bad.append('data/events.json: "needsConfirmation" is true - the 2026 dates '
                           "are not yet confirmed by the samaj")
        except (json.JSONDecodeError, AttributeError) as exc:
            bad.append(f"data/events.json: cannot be read ({exc})")
    return bad


def problems(root: Path) -> list[str]:
    bad = []
    for page in pages(root):
        rel = page.relative_to(root)
        seen = {}
        for key, attr, attrs in head_tags(page.read_text(encoding="utf-8")):
            seen[key] = attrs[attr]
        for key in sorted(required_keys(root, page) - seen.keys()):
            bad.append(f"{rel}: missing tag {key}")
        for key, url in sorted(seen.items()):
            if not url.startswith("https://"):
                bad.append(f"{rel}: {key} is not absolute: {url!r}")
    robots = root / "robots.txt"
    if not robots.exists():
        bad.append("robots.txt: missing")
    elif PLACEHOLDER in robots.read_text(encoding="utf-8"):
        bad.append(f"robots.txt: still contains {PLACEHOLDER}")
    elif "Sitemap: https://" not in robots.read_text(encoding="utf-8"):
        bad.append("robots.txt: no absolute Sitemap line")
    if not (root / "sitemap.xml").exists():
        bad.append("sitemap.xml: missing (run tools/set_domain.py DOMAIN)")
    hosts = hosts_in(root)
    if len(hosts) > 1:
        detail = "; ".join(f"{h} ({', '.join(sorted(f)[:3])}{'...' if len(f) > 3 else ''})"
                           for h, f in sorted(hosts.items()))
        bad.append(f"more than one host in use: {detail}")
    bad.extend(placeholder_problems(root))
    return bad


def run_check(root: Path) -> int:
    bad = problems(root)
    for line in bad:
        print(line)
    if bad:
        print(f"\nNOT READY TO PUBLISH: {len(bad)} problem(s). "
              "Run: python3 tools/set_domain.py YOUR-DOMAIN")
        return 1
    host = next(iter(hosts_in(root)))
    print(f"Ready: every page has all tags, all absolute, one host ({host}).")
    return 0


def dirty_warning(root: Path) -> None:
    if not (root / ".git").exists():
        return
    try:
        out = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return
    if out.strip():
        print("WARNING: git tree has uncommitted changes; commit them first so the sweep "
              "shows up alone in `git diff` and can be undone with `git checkout -- .`")


def already_swept(root: Path) -> str | None:
    hosts = hosts_in(root)
    if hosts:
        return ", ".join(sorted(hosts))
    robots = root / "robots.txt"
    if robots.exists() and PLACEHOLDER not in robots.read_text(encoding="utf-8"):
        return "(robots.txt has no placeholder)"
    return None


def run_sweep(root: Path, domain: str, force: bool) -> int:
    base = normalize_domain(domain)
    existing = already_swept(root)
    if existing and not force:
        print(f"REFUSED: this site was already swept (host: {existing}).\n"
              f"Re-running could leave a mix of hosts. If you really mean to switch to "
              f"{base}, add --force:\n  python3 tools/set_domain.py {domain} --force\n"
              "To undo an uncommitted sweep: git checkout -- .")
        return 1
    dirty_warning(root)
    changed = []
    for page in pages(root):
        old = page.read_text(encoding="utf-8")
        new = sweep_html(old, base, force)
        if new != old:
            page.write_text(new, encoding="utf-8")
            changed.append(str(page.relative_to(root)))
    robots = root / "robots.txt"
    if robots.exists():
        text = robots.read_text(encoding="utf-8").replace(PLACEHOLDER, base.removeprefix("https://"))
        text = re.sub(r"(?m)^Sitemap:\s*\S+$", f"Sitemap: {base}/sitemap.xml", text)
        robots.write_text(text, encoding="utf-8")
        changed.append("robots.txt")
    n = write_sitemap(root, domain)
    changed.append("sitemap.xml")
    print(f"Domain applied: {base}\nFiles changed ({len(changed)}):")
    for c in changed:
        print(f"  {c}")
    print(f"Sitemap lists {n} pages.\n")
    return run_check(root)


def main(argv: list[str]) -> int:
    args = argv[1:]
    root = Path(__file__).resolve().parent.parent
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        del args[i:i + 2]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    if args == ["--check"]:
        return run_check(root)
    if len(args) != 1 or args[0].startswith("-"):
        print(__doc__)
        return 2
    try:
        return run_sweep(root, args[0], force)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
