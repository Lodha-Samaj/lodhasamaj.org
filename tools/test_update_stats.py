"""The दान and home sheets are generated; these tests keep them honest.

A list that changes without tools/update_stats.py being re-run leaves both
pages claiming yesterday's figures, so --check runs here.
"""
import json
import re
from pathlib import Path

import pytest

from update_stats import (CARDS, ROOT, _labels, amount, goods_columns, group_name,
                          home_block, home_groups, indian_grouping, main, read_list,
                          sheet, totals)

TYPES, UNITS = _labels("TYPE_LABELS"), _labels("UNIT_LABELS")


def test_the_daan_and_home_pages_carry_the_current_figures():
    assert main(["--check"]) == 0, (
        "the sheets are stale - run python3 tools/update_stats.py")


def test_the_home_sheet_shows_every_year_of_every_aayojan():
    index = json.loads((ROOT / "data" / "donors-index.json").read_text(encoding="utf-8"))
    keys = [key for g in home_groups() for key in g["lists"]]
    assert sorted(keys) == sorted([str(y) for y in index["years"]] + index["lists"])
    for lang in ("hi", "en"):
        block = home_block(lang, TYPES, UNITS)
        assert block.count('class="sheet-row"') == len(keys)
        for year in index["years"]:
            assert f"<h3>{year}</h3>" in block, (lang, year)
    # The आयोजन is named once, with no year on it.
    for group in home_groups():
        for lang in ("hi", "en"):
            assert not re.search(r"(?:19|20)\d{2}", group_name(group, lang)), group["slug"]


def test_the_home_page_no_longer_carries_the_three_hand_picked_donors():
    for lang in ("hi", "en"):
        src = (ROOT / lang / "index.html").read_text(encoding="utf-8")
        assert "donor-roll" not in src and "donor-card" not in src, lang
        assert '<!-- sheet:home -->' in src, lang


def test_every_card_shows_the_lists_it_names():
    pages = {lang: (ROOT / lang / "daan" / "index.html").read_text(encoding="utf-8")
             for lang in ("hi", "en")}
    for card in CARDS:
        for lang, src in pages.items():
            block = src[src.index(f'<!-- sheet:{card["slug"]} -->'):
                        src.index(f'<!-- /sheet:{card["slug"]} -->')]
            assert block.count('class="sheet-row"') == len(card["lists"]), card["slug"]
            for key in card["lists"]:
                year = re.search(r"((?:19|20)\d{2})$", key)
                want = f"<h3>{year.group(1)}</h3>" if year else "<h3>अब तक</h3>"
                if lang == "en" and not year:
                    want = "<h3>so far</h3>"
                assert want in block, (card["slug"], key, lang, want)


def test_a_line_carries_that_lists_own_donor_count_and_cash():
    for card in CARDS:
        block = sheet(card, "hi", TYPES, UNITS)
        for key in card["lists"]:
            donors = read_list(key)["donors"]
            cash = next((q for (kind, _u), q in totals(donors).items() if kind == "cash"), None)
            assert f"<b>{len(donors)}</b><span>दानदाता</span>" in block, (card["slug"], key)
            if cash:
                assert f"<b>₹{indian_grouping(int(cash))}</b>" in block, (card["slug"], key)


def test_a_cards_three_kinds_are_the_ones_it_is_mostly_given():
    # The मंदिर is built of ईंट, सीमेंट and सरिया; the भंडारा is fed with आटा,
    # शक्कर and मावा - the समाज asked for मावा by name.
    assert goods_columns(next(c for c in CARDS if c["slug"] == "temple")) == \
        ["brick", "cement", "rebar"]
    assert sorted(goods_columns(next(c for c in CARDS if c["slug"] == "festival"))) == \
        ["flour", "mawa", "sugar"]
    # Both years of a card show the same two kinds, or the lines cannot be compared.
    for card in CARDS:
        block = sheet(card, "hi", TYPES, UNITS)
        for row in re.findall(r'<div class="sheet-row">.*?</div>', block, flags=re.S):
            for kind in card.get("goods", goods_columns(card)):
                assert TYPES[kind]["hi"] in row, (card["slug"], kind)


def test_labels_come_from_donors_core_so_the_pages_cannot_drift():
    assert amount(("flour", "kg"), 1174, "hi", TYPES, UNITS) == ("1,174 किलो", "आटा")
    assert amount(("cement", "bag"), 122, "en", TYPES, UNITS) == ("122 bags", "Cement")
    assert amount(("brick", "count"), 551, "hi", TYPES, UNITS) == ("551", "ईंट")
    assert amount(("cash", "inr"), 36343, "hi", TYPES, UNITS) == ("₹36,343", "नगद")


@pytest.mark.parametrize("n,want", [(900, "900"), (47305, "47,305"), (233206, "2,33,206")])
def test_indian_grouping_is_what_the_site_renders(n, want):
    assert indian_grouping(n) == want
