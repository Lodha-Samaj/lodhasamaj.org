"""Tests for set_domain.py / make_sitemap.py.

They build SYNTHETIC pages, so they stay valid before and after the real site
has been swept. Only the last tests look at the real pages, and only for
properties that hold either way.
"""
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import make_sitemap
import set_domain

REPO = Path(__file__).resolve().parent.parent
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}

PAGE = '''<!DOCTYPE html>
<html lang="{lang}"><head>
  <!-- TASK 11: canonical must become absolute -->
  <link rel="canonical" href="/{lang}/{path}/">
  <link rel="alternate" hreflang="hi" href="/hi/{path}/">
  <link rel="alternate" hreflang="en" href="/en/{path}/">
  <link rel="alternate" hreflang="x-default" href="/hi/{path}/">
  <meta property="og:url" content="/{lang}/{path}/">
  <meta property="og:image" content="/assets/img/logo-social.png">
  <link rel="stylesheet" href="/assets/css/site.css">
</head><body><a href="/{lang}/">home</a></body></html>
'''


def A(*a):
    return ["set_domain.py", *a]


@pytest.fixture
def site(tmp_path):
    for lang in ("hi", "en"):
        for path in ("parichay", "daan/2025"):
            d = tmp_path / lang / path
            d.mkdir(parents=True)
            (d / "index.html").write_text(PAGE.format(lang=lang, path=path), encoding="utf-8")
    (tmp_path / "index.html").write_text(
        '<html><head><link rel="canonical" href="/hi/"></head></html>', encoding="utf-8")
    (tmp_path / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: https://{set_domain.PLACEHOLDER}/sitemap.xml\n")
    return tmp_path


def sweep(site, domain="first.test", *extra):
    return set_domain.main(A(domain, *extra, "--root", str(site)))


def test_check_fails_before_the_sweep(site, capsys):
    assert set_domain.main(A("--check", "--root", str(site))) == 1
    assert "NOT READY TO PUBLISH" in capsys.readouterr().out


def test_sweep_makes_everything_absolute_and_ready(site):
    assert sweep(site) == 0
    page = (site / "en/daan/2025/index.html").read_text(encoding="utf-8")
    assert '<meta property="og:image" content="https://first.test/assets/img/logo-social.png">' in page
    assert '<link rel="canonical" href="https://first.test/en/daan/2025/">' in page
    assert 'href="/assets/css/site.css"' in page and 'href="/en/">' in page
    assert "Sitemap: https://first.test/sitemap.xml" in (site / "robots.txt").read_text()
    assert set_domain.main(A("--check", "--root", str(site))) == 0


def test_sweep_prints_domain_and_files(site, capsys):
    sweep(site)
    out = capsys.readouterr().out
    assert "Domain applied: https://first.test" in out and "robots.txt" in out and "sitemap.xml" in out


def test_second_run_with_another_domain_is_refused_and_changes_nothing(site, capsys):
    sweep(site, "first.test")
    snap = {p: p.read_bytes() for p in site.rglob("*") if p.is_file()}
    assert sweep(site, "second.test") == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out and "first.test" in out and "--force" in out
    assert {p: p.read_bytes() for p in site.rglob("*") if p.is_file()} == snap


def test_force_moves_everything_to_the_new_host(site):
    sweep(site, "first.test")
    assert sweep(site, "second.test", "--force") == 0
    assert set(set_domain.hosts_in(site)) == {"second.test"}
    assert set_domain.main(A("--check", "--root", str(site))) == 0


def test_check_catches_a_mixed_site(site, capsys):
    sweep(site, "first.test")
    p = site / "hi/parichay/index.html"
    p.write_text(p.read_text(encoding="utf-8").replace("first.test", "other.test"), encoding="utf-8")
    assert set_domain.main(A("--check", "--root", str(site))) == 1
    assert "more than one host" in capsys.readouterr().out


@pytest.mark.parametrize("needle", ['<meta property="og:image" content="https://first.test/assets/img/logo-social.png">',
                                    '<link rel="canonical" href="https://first.test/hi/parichay/">'])
def test_check_catches_a_deleted_tag(site, capsys, needle):
    sweep(site)
    p = site / "hi/parichay/index.html"
    text = p.read_text(encoding="utf-8")
    assert needle in text
    p.write_text(text.replace(needle, ""), encoding="utf-8")
    assert set_domain.main(A("--check", "--root", str(site))) == 1
    assert "hi/parichay/index.html: missing tag" in capsys.readouterr().out


def test_reordered_attributes_are_still_read(site):
    p = site / "hi/parichay/index.html"
    p.write_text(p.read_text(encoding="utf-8").replace(
        '<meta property="og:image" content="/assets/img/logo-social.png">',
        '<meta content="/assets/img/logo-social.png" property="og:image">'), encoding="utf-8")
    assert sweep(site) == 0
    assert 'content="https://first.test/assets/img/logo-social.png" property="og:image"' in p.read_text(encoding="utf-8")


def test_check_catches_a_robots_placeholder(site):
    sweep(site)
    (site / "robots.txt").write_text(f"Sitemap: https://{set_domain.PLACEHOLDER}/sitemap.xml\n")
    assert set_domain.main(A("--check", "--root", str(site))) == 1


@pytest.mark.parametrize("bad", ["", "nodot", "REPLACE-WITH-DOMAIN", "a.com/path", "has space.com"])
def test_bad_domains_are_refused_and_nothing_changes(site, bad):
    snap = {p: p.read_bytes() for p in site.rglob("*") if p.is_file()}
    assert sweep(site, bad) == 2
    assert {p: p.read_bytes() for p in site.rglob("*") if p.is_file()} == snap


def test_sitemap_lists_every_page_on_disk_with_alternates(site):
    make_sitemap.write(site, "test.example")
    root = ET.parse(site / "sitemap.xml").getroot()
    locs = {u.find("s:loc", NS).text for u in root.findall("s:url", NS)}
    assert locs == {"https://test.example/" + p.parent.relative_to(site).as_posix() + "/"
                    for lang in ("hi", "en") for p in (site / lang).rglob("index.html")}
    entry = next(u for u in root.findall("s:url", NS)
                 if u.find("s:loc", NS).text == "https://test.example/en/daan/2025/")
    assert {a.get("hreflang"): a.get("href") for a in entry.findall("x:link", NS)} == {
        "en": "https://test.example/en/daan/2025/",
        "hi": "https://test.example/hi/daan/2025/",
        "x-default": "https://test.example/hi/daan/2025/"}


def test_new_donor_year_appears_without_editing_anything(site):
    for lang in ("hi", "en"):
        d = site / lang / "daan" / "2026"
        d.mkdir()
        (d / "index.html").write_text("<!DOCTYPE html>", encoding="utf-8")
    make_sitemap.write(site, "test.example")
    text = (site / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://test.example/hi/daan/2026/" in text and "https://test.example/en/daan/2026/" in text


def test_page_without_counterpart_gets_no_alternates(tmp_path):
    (tmp_path / "hi" / "only").mkdir(parents=True)
    (tmp_path / "hi" / "only" / "index.html").write_text("x")
    (tmp_path / "en").mkdir()
    make_sitemap.write(tmp_path, "test.example")
    assert "xhtml:link" not in (tmp_path / "sitemap.xml").read_text()


# --- the real pages: only properties that hold before AND after the real sweep ---

def test_every_real_page_carries_all_head_tags():
    root = REPO
    missing = []
    for page in set_domain.pages(root):
        seen = {k for k, _, _ in set_domain.head_tags(page.read_text(encoding="utf-8"))}
        missing += [f"{page.relative_to(root)}: {k}" for k in sorted(set_domain.required_keys(root, page) - seen)]
    assert missing == []


def test_sweep_works_on_a_copy_of_the_real_pages_in_either_state(tmp_path):
    for name in ("hi", "en"):
        shutil.copytree(REPO / name, tmp_path / name)
    shutil.copy(REPO / "index.html", tmp_path / "index.html")
    (tmp_path / "robots.txt").write_text(f"Sitemap: https://{set_domain.PLACEHOLDER}/sitemap.xml\n")
    # the exit code also reflects live placeholders in the real pages, which is
    # a separate gate (tested below); this test is only about the hosts.
    set_domain.main(A("copy.test", "--force", "--root", str(tmp_path)))
    assert set(set_domain.hosts_in(tmp_path)) == {"copy.test"}


def test_check_refuses_the_placeholder_email(site):
    sweep(site)
    p = site / "hi/parichay/index.html"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "</body>", '<a href="mailto:info@example.org">x</a></body>'), encoding="utf-8")
    assert set_domain.main(A("--check", "--root", str(site))) == 1


def test_placeholder_inside_a_comment_is_not_a_problem(site):
    sweep(site)
    p = site / "hi/parichay/index.html"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "</body>", "<!-- REVIEW: info@example.org -->\n</body>"), encoding="utf-8")
    assert set_domain.main(A("--check", "--root", str(site))) == 0


def test_check_refuses_while_events_need_confirmation(site, capsys):
    sweep(site)
    (site / "data").mkdir()
    (site / "data/events.json").write_text('{"needsConfirmation": true, "events": []}')
    assert set_domain.main(A("--check", "--root", str(site))) == 1
    assert "needsConfirmation" in capsys.readouterr().out
    (site / "data/events.json").write_text('{"events": []}')
    assert set_domain.main(A("--check", "--root", str(site))) == 0



# --- a stray copy of the site must not be treated as part of the site ---
# Found when the branch was merged: run from the main checkout, pages() walked
# into .claude/worktrees/<name>/ and returned 49 pages instead of 23. The launch
# sweep would have rewritten that copy and listed its paths in the public
# sitemap. Fixtures are synthetic so these keep passing after the real sweep.

def test_pages_skips_dot_directories(tmp_path):
    (tmp_path / "hi").mkdir()
    (tmp_path / "hi" / "index.html").write_text("<html></html>", encoding="utf-8")
    for buried in (".claude/worktrees/wt/hi", ".git/x", ".playwright-mcp", "node_modules/pkg"):
        d = tmp_path / buried
        d.mkdir(parents=True)
        (d / "index.html").write_text("<html></html>", encoding="utf-8")
    found = [p.relative_to(tmp_path).as_posix() for p in set_domain.pages(tmp_path)]
    assert found == ["hi/index.html"], found


def test_site_file_guard_matches_check_links(tmp_path):
    """The two walkers must agree on what counts as a site file."""
    import check_links
    (tmp_path / ".claude" / "worktrees" / "wt").mkdir(parents=True)
    stray = tmp_path / ".claude" / "worktrees" / "wt" / "index.html"
    stray.write_text('<a href="/nowhere/">x</a>', encoding="utf-8")
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    # set_domain excludes it...
    assert stray not in set_domain.pages(tmp_path)
    # ...and check_links must not report its broken link either.
    assert check_links.find_broken(str(tmp_path)) == []
