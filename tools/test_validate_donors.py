import json
from pathlib import Path
import pytest
from validate_donors import validate_file, main, TYPES, UNITS


def write(tmp_path: Path, payload, name="donors-2025.json") -> str:
    p = tmp_path / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(p)


VALID = {
    "year": 2025,
    "festival": {"bhandara": 45, "kanyaPujan": 22},
    "donors": [
        {"name": {"hi": "श्री संजय जी जमदार"}, "items": [{"type": "sugar", "qty": 501, "unit": "kg"}]}
    ],
}


def test_valid_file_has_no_errors(tmp_path):
    assert validate_file(write(tmp_path, VALID)) == []


def test_malformed_json_reports_one_clear_error(tmp_path):
    p = tmp_path / "donors-2026.json"
    p.write_text('{"year": 2026, "donors": [],}', encoding="utf-8")  # trailing comma
    errors = validate_file(str(p))
    assert len(errors) == 1
    assert "JSON" in errors[0]


def test_year_must_match_filename(tmp_path):
    bad = {**VALID, "year": 2024}
    errors = validate_file(write(tmp_path, bad, "donors-2025.json"))
    assert any("filename" in e for e in errors)


def test_missing_hindi_name_is_an_error(tmp_path):
    bad = {**VALID, "donors": [{"name": {"en": "Someone"}, "items": []}]}
    errors = validate_file(write(tmp_path, bad))
    assert any("name.hi" in e for e in errors)


def test_unknown_type_is_reported_with_the_donor_name(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क ख ग"}, "items": [{"type": "sakkar", "qty": 1, "unit": "kg"}]}
    ]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "sakkar" in errors[0] and "श्री क ख ग" in errors[0]


def test_unknown_unit_is_reported(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क"}, "items": [{"type": "sugar", "qty": 1, "unit": "quintal"}]}
    ]}
    assert any("quintal" in e for e in validate_file(write(tmp_path, bad)))


def test_non_numeric_qty_is_reported_but_is_not_fatal_elsewhere(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री ग"}, "items": [{"type": "sugar", "qty": "इक्यावन", "unit": "kg"}]}
    ]}
    assert any("qty" in e for e in validate_file(write(tmp_path, bad)))


def test_item_without_qty_is_allowed(tmp_path):
    ok = {**VALID, "donors": [
        {"name": {"hi": "श्री मनोहर जी वर्मा"},
         "items": [{"type": "pattal", "note": "सम्पूर्ण भंडारे हेतु"}]}
    ]}
    assert validate_file(write(tmp_path, ok)) == []


def test_vocabularies_match_the_spec():
    assert TYPES == {"sugar", "flour", "oil", "salt", "ghee", "mawa", "cash",
                     "water", "gas", "coconut", "pattal", "besan", "rava",
                     "rice", "cement", "brick", "rebar", "tiles", "fan",
                     "other"}
    assert UNITS == {"kg", "tin", "inr", "jar", "cylinder", "piece", "bag", "count"}


def test_non_object_donor_is_reported_not_raised(tmp_path):
    bad = {**VALID, "donors": ["just a name"]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "donor #1" in errors[0] and "must be an object" in errors[0]


def test_non_object_item_is_reported_not_raised(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क ख"}, "items": ["sugar 501 kg"]}
    ]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "श्री क ख" in errors[0] and "item #1" in errors[0]


def test_non_object_name_is_reported_not_raised(tmp_path):
    bad = {**VALID, "donors": [{"name": "श्री क", "items": []}]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "donor #1" in errors[0] and "'name' must be an object" in errors[0]


def test_non_string_name_hi_is_reported_not_raised(tmp_path):
    bad = {**VALID, "donors": [{"name": {"hi": 5}, "items": []}]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "donor #1" in errors[0] and "name.hi must be text, got int" in errors[0]


def test_non_object_top_level_is_reported_not_raised(tmp_path):
    errors = validate_file(write(tmp_path, []))
    assert len(errors) == 1
    assert "top level must be an object" in errors[0]


def test_bool_year_is_rejected(tmp_path):
    bad = {**VALID, "year": True}
    errors = validate_file(write(tmp_path, bad))
    assert any("'year' must be an integer" in e for e in errors)


def test_bool_qty_is_rejected(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क"}, "items": [{"type": "sugar", "qty": True, "unit": "kg"}]}
    ]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "'qty' must be a finite number" in errors[0]


def test_nan_qty_is_rejected(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क"}, "items": [{"type": "sugar", "qty": float("nan"), "unit": "kg"}]}
    ]}
    errors = validate_file(write(tmp_path, bad))
    assert len(errors) == 1
    assert "'qty' must be a finite number" in errors[0]


def test_item_errors_name_the_item_position(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क"}, "items": [
            {"type": "sugar", "qty": 1, "unit": "kg"},
            {"type": "sakkar", "qty": 1, "unit": "kg"},
            {"type": "sugar", "qty": "x", "unit": "quintal"},
        ]}
    ]}
    errors = validate_file(write(tmp_path, bad))
    assert any("item #2" in e and "sakkar" in e for e in errors)
    assert any("item #3" in e and "quintal" in e for e in errors)
    assert any("item #3" in e and "'qty'" in e for e in errors)


def page_html(lang: str, year: int, data_year=None) -> str:
    u = f"/{lang}/daan/{year}/"
    return (f'<link rel="canonical" href="{u}">\n'
            f'<link rel="alternate" hreflang="{lang}" href="{u}">\n'
            f'<meta property="og:url" content="{u}">\n'
            f'<body data-year="{data_year or year}">')


def make_pages(root: Path, year: int, langs=("hi", "en")) -> None:
    for lang in langs:
        d = root / lang / "daan" / str(year)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page_html(lang, year), encoding="utf-8")


def test_index_is_not_validated_as_a_donor_file(tmp_path, capsys):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    make_pages(tmp_path, 2025)
    assert main(["validate_donors.py"], data_dir=tmp_path, site_root=tmp_path) == 0
    out = capsys.readouterr().out
    assert "1 file(s) checked, 0 error(s)" in out


def test_index_lists_missing_year_file(tmp_path, capsys):
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    assert main(["validate_donors.py"], data_dir=tmp_path) == 1
    assert "donors-index.json lists 2025 but data/donors-2025.json is missing" in capsys.readouterr().out


def test_year_file_not_listed_in_index(tmp_path, capsys):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": []}, "donors-index.json")
    assert main(["validate_donors.py"], data_dir=tmp_path) == 1
    assert "data/donors-2025.json exists but donors-index.json does not list it" in capsys.readouterr().out


def test_clean_directory_exits_zero(tmp_path, capsys):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    make_pages(tmp_path, 2025)
    assert main(["validate_donors.py"], data_dir=tmp_path, site_root=tmp_path) == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_listed_year_with_data_but_no_page_directory_is_reported(tmp_path, capsys):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    # data file and index entry exist, but no hi/daan/2025 or en/daan/2025
    assert main(["validate_donors.py"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "hi/daan/2025/index.html is missing" in out
    assert "en/daan/2025/index.html is missing" in out


def test_only_one_language_page_missing_names_that_path(tmp_path, capsys):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    make_pages(tmp_path, 2025, langs=("hi",))
    assert main(["validate_donors.py"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "en/daan/2025/index.html is missing" in out
    assert "hi/daan/2025/index.html is missing" not in out


def _setup(tmp_path, index_text):
    write(tmp_path, VALID, "donors-2025.json")
    (tmp_path / "donors-index.json").write_text(index_text, encoding="utf-8")
    make_pages(tmp_path, 2025)


def test_stale_data_year_is_reported(tmp_path, capsys):
    _setup(tmp_path, '{"years": [2025]}')
    (tmp_path / "hi/daan/2025/index.html").write_text(
        page_html("hi", 2025, data_year=2024), encoding="utf-8")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert 'hi/daan/2025/index.html: expected data-year="2025" but found 2024' in out


def test_stale_canonical_ogurl_and_hreflang_are_reported(tmp_path, capsys):
    _setup(tmp_path, '{"years": [2025]}')
    (tmp_path / "en/daan/2025/index.html").write_text(
        page_html("en", 2024).replace('data-year="2024"', 'data-year="2025"'), encoding="utf-8")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "canonical should contain /daan/2025/" in out
    assert "og:url should contain /daan/2025/" in out
    assert 'hreflang="en" should contain /daan/2025/' in out


def test_index_trailing_comma_reports_line_and_column(tmp_path, capsys):
    _setup(tmp_path, '{"years": [2025,]}')
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "donors-index.json: invalid JSON at line 1, column" in out


def test_index_without_years_key(tmp_path, capsys):
    _setup(tmp_path, '{"yrs": [2025]}')
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    assert "must be an object with a 'years' list" in capsys.readouterr().out


def test_index_digit_string_year_gets_one_specific_message(tmp_path, capsys):
    _setup(tmp_path, '{"years": ["2025"]}')
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert 'year "2025" is in quotes' in out
    assert "is missing" not in out and "does not list" not in out


def test_nonexistent_explicit_path_is_an_error_not_a_traceback(tmp_path, capsys):
    assert main(["v", str(tmp_path / "nope.json")], data_dir=tmp_path) == 1
    assert "cannot read the file" in capsys.readouterr().out


def test_qty_without_unit_is_an_error(tmp_path):
    bad = {**VALID, "donors": [
        {"name": {"hi": "श्री क"}, "items": [{"type": "sugar", "qty": 51}]}]}
    assert any("no 'unit'" in e for e in validate_file(write(tmp_path, bad)))


# ---- named lists (data-list), e.g. the श्री हनुमान मंदिर निर्माण campaign ----

LIST = {"list": "hanuman-mandir",
        "title": {"hi": "श्री हनुमान मंदिर निर्माण", "en": "Shri Hanuman Temple Construction"},
        "donors": [{"name": {"hi": "श्री धन्नालाल जाट"},
                    "items": [{"type": "brick", "qty": 551, "unit": "count"},
                              {"type": "cement", "qty": 21, "unit": "bag"}]}]}


def make_list_pages(root: Path, slug: str, langs=("hi", "en")) -> None:
    for lang in langs:
        d = root / lang / "daan" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(f'<body data-list="{slug}">', encoding="utf-8")


def test_named_list_file_is_valid_without_a_year(tmp_path):
    assert validate_file(write(tmp_path, LIST, "hanuman-mandir.json")) == []


def test_named_list_must_name_itself_and_carry_a_hindi_title(tmp_path):
    bad = {**LIST, "list": "mandir", "title": {"en": "Temple"}}
    errors = validate_file(write(tmp_path, bad, "hanuman-mandir.json"))
    assert any("'list' is 'mandir' but the filename says hanuman-mandir" in e for e in errors)
    assert any("title.hi" in e for e in errors)


def _site(tmp_path):
    write(tmp_path, VALID, "donors-2025.json")
    write(tmp_path, {"years": [2025]}, "donors-index.json")
    make_pages(tmp_path, 2025)


def test_a_page_pointing_at_a_named_list_gets_that_file_checked(tmp_path, capsys):
    _site(tmp_path)
    make_list_pages(tmp_path, "hanuman-mandir")
    write(tmp_path, {**LIST, "donors": [{"name": {"hi": "x"}, "items": [{"type": "sement"}]}]},
          "hanuman-mandir.json")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    out = capsys.readouterr().out
    assert "unknown type 'sement'" in out
    assert "2 file(s) checked" in out


def test_a_page_pointing_at_a_missing_list_file_is_reported(tmp_path, capsys):
    _site(tmp_path)
    make_list_pages(tmp_path, "hanuman-mandir")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    assert ("hi/daan/hanuman-mandir/index.html shows data-list=\"hanuman-mandir\" "
            "but data/hanuman-mandir.json is missing") in capsys.readouterr().out


def test_a_named_list_needs_a_page_in_both_languages(tmp_path, capsys):
    _site(tmp_path)
    make_list_pages(tmp_path, "hanuman-mandir", langs=("hi",))
    write(tmp_path, LIST, "hanuman-mandir.json")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 1
    assert ("data-list=\"hanuman-mandir\" has a hi page but no en page"
            in capsys.readouterr().out)


def test_a_complete_named_list_passes(tmp_path, capsys):
    _site(tmp_path)
    make_list_pages(tmp_path, "hanuman-mandir")
    write(tmp_path, LIST, "hanuman-mandir.json")
    assert main(["v"], data_dir=tmp_path, site_root=tmp_path) == 0
