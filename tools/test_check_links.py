from pathlib import Path
from check_links import find_broken


def site(tmp_path: Path, pages: dict[str, str], assets: list[str] = ()) -> Path:
    for name in assets:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    for name, body in pages.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return tmp_path


def test_resolvable_root_relative_link_is_not_reported(tmp_path):
    root = site(tmp_path,
                {"hi/index.html": '<a href="/hi/daan/">d</a><img src="/assets/img/logo.png">'},
                ["hi/daan/index.html", "assets/img/logo.png"])
    assert find_broken(str(root)) == []


def test_missing_asset_is_reported_with_its_source_page(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<img src="/assets/img/missing.png">'})
    broken = find_broken(str(root))
    assert len(broken) == 1
    assert "missing.png" in broken[0] and "hi/index.html" in broken[0]


def test_external_mail_tel_and_anchor_links_are_skipped(tmp_path):
    root = site(tmp_path, {"hi/index.html":
        '<a href="https://x.org/a">a</a><a href="mailto:a@b.org">m</a>'
        '<a href="tel:+911234567890">t</a><a href="#top">top</a>'})
    assert find_broken(str(root)) == []


def test_directory_link_resolves_to_its_index_html(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href="/hi/daan/">d</a>'},
                ["hi/daan/index.html"])
    assert find_broken(str(root)) == []


def test_relative_link_is_resolved_against_the_page(tmp_path):
    root = site(tmp_path, {"hi/daan/index.html": '<a href="2025/">y</a>'},
                ["hi/daan/2025/index.html"])
    assert find_broken(str(root)) == []


def test_single_quoted_and_unquoted_values_are_checked(tmp_path):
    root = site(tmp_path, {"hi/index.html":
        '<a href="/gone-a/">a</a><a href=\'/gone-b/\'>b</a>'
        '<a href=/gone-c/>c</a><A HREF="/gone-d/">d</A>'})
    broken = find_broken(str(root))
    assert len(broken) == 4
    for name in ("gone-a", "gone-b", "gone-c", "gone-d"):
        assert any(name in item for item in broken)


def test_unquoted_value_stops_before_a_following_attribute(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href=/gone-c/ class=x>c</a>'})
    broken = find_broken(str(root))
    assert broken == ["hi/index.html -> /gone-c/"]


def test_uppercase_scheme_links_are_skipped(tmp_path):
    root = site(tmp_path, {"hi/index.html":
        '<a href="HTTP://example.com/a">a</a>'
        '<a href="MAILTO:someone@example.org">m</a>'
        '<a href="Https://example.com/b">b</a>'})
    assert find_broken(str(root)) == []


def test_attribute_text_inside_a_script_block_is_not_reported(tmp_path):
    body = (
        '<script type="module">\n'
        '  img.src = thumbUrl;\n'
        '  el.innerHTML = `<a href=${url}>x</a>`;\n'
        "  const s = 'href=/not-a-link/';\n"
        '</script>'
    )
    root = site(tmp_path, {"hi/index.html": body})
    assert find_broken(str(root)) == []


def test_attribute_text_inside_an_html_comment_is_not_reported(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<!-- <a href="/retired-page/">x</a> -->'})
    assert find_broken(str(root)) == []


def test_real_link_after_a_script_block_is_still_reported(tmp_path):
    root = site(tmp_path, {"hi/index.html":
        '<script>const s = 1;</script><a href="/gone/">x</a>'})
    assert find_broken(str(root)) == ["hi/index.html -> /gone/"]


def test_missing_script_src_is_still_reported(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<script src="/missing.js"></script>'})
    assert find_broken(str(root)) == ["hi/index.html -> /missing.js"]


def test_empty_href_is_skipped(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href="">e</a>'})
    assert find_broken(str(root)) == []


def test_gt_inside_quotes_is_part_of_the_value(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href="/a>b/">x</a>'})
    assert find_broken(str(root)) == ["hi/index.html -> /a>b/"]


def test_apostrophe_inside_double_quotes_is_part_of_the_value(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href="/a\'b/">x</a>'})
    assert find_broken(str(root)) == ["hi/index.html -> /a'b/"]


def test_double_quote_inside_single_quotes_is_part_of_the_value(tmp_path):
    root = site(tmp_path, {"hi/index.html": "<a href='/a\"b/'>x</a>"})
    assert find_broken(str(root)) == ['hi/index.html -> /a"b/']


def test_whitespace_around_the_equals_sign_is_allowed(tmp_path):
    root = site(tmp_path, {"hi/index.html": '<a href = "/x/">x</a>'})
    assert find_broken(str(root)) == ["hi/index.html -> /x/"]
