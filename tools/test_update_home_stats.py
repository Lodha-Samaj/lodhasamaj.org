"""The home page's cards are generated; these tests keep them honest.

A list that changes without tools/update_home_stats.py being re-run leaves the
home page claiming yesterday's figures, so --check runs here. The rest guard
the arithmetic and the labels the cards are built from.
"""
import json
import re
from pathlib import Path

import pytest

from update_home_stats import (ROOT, _labels, block, figure, group_title,
                               indian_grouping, ledgers, main, totals)

INDEX = json.loads((ROOT / "data" / "donors-index.json").read_text(encoding="utf-8"))
TYPES, UNITS = _labels("TYPE_LABELS"), _labels("UNIT_LABELS")


def test_the_home_pages_carry_the_current_figures():
    assert main(["--check"]) == 0, (
        "the home page cards are stale - run python3 tools/update_home_stats.py")


def test_every_list_in_the_index_gets_a_line():
    groups = ledgers(INDEX)
    keys = [row["key"] for g in groups for row in g["rows"]]
    assert sorted(keys) == sorted([str(y) for y in INDEX["years"]] + INDEX["lists"])
    # One आयोजन per block, its years newest first, and the मंदिर last.
    assert [g["kind"] for g in groups] == ["festival", "yatra", "mandir"]
    for g in groups:
        years = [r["year"] for r in g["rows"] if r["year"]]
        assert years == sorted(years, reverse=True)
    assert groups[-1]["rows"][0]["key"] == "hanuman-mandir"


def test_a_group_is_named_once_without_its_year():
    # "श्री नर्मदेश्वर महादेव भव्य कावड़ यात्रा 2026" titles one list; the block
    # above three such lists must not carry any one of their years.
    yatra = next(g for g in ledgers(INDEX) if g["kind"] == "yatra")
    for lang in ("hi", "en"):
        title = group_title(yatra, lang)
        assert not re.search(r"\d{4}", title), title
    assert group_title(ledgers(INDEX)[0], "hi") == "नवदुर्गा महोत्सव एवं विशाल भंडारा"


def test_a_lines_figures_are_the_lists_own_totals():
    year = max(INDEX["years"])
    donors = json.loads((ROOT / "data" / f"donors-{year}.json").read_text(encoding="utf-8"))["donors"]
    cash = totals(donors)[("cash", "inr")]
    html = block("hi", INDEX, TYPES, UNITS)
    card = html[html.index(f"navdurga-mahotsav-{year}"):]
    card = card[:card.index("</li>")]  # that year's line
    assert f"₹{indian_grouping(int(cash))}" in card
    assert f"{len(donors)} दानदाता" in card


def test_cash_leads_a_line_and_then_the_largest_quantities():
    html = block("hi", INDEX, TYPES, UNITS)
    card = html[html.index("hanuman-mandir"):]
    card = card[:card.index("</li>")]
    figures = re.findall(r'<span class="fig"><b>([^<]+)</b> ([^<]+)</span>', card)
    assert figures[0][1] == "नगद"
    assert ("551", "ईंट") in [(a.split()[0], b) for a, b in figures]


def test_labels_come_from_donors_core_so_the_pages_cannot_drift():
    assert TYPES["mawa"]["hi"] == "मावा" and TYPES["mawa"]["en"] == "Mawa"
    assert UNITS["bag"]["hi"] == "बोरी" and UNITS["bag"]["enPlural"] == "bags"
    assert figure(("flour", "kg"), 1174, "hi", TYPES, UNITS) == ("1,174 किलो", "आटा")
    assert figure(("oil", "tin"), 6, "en", TYPES, UNITS) == ("6 tins", "Oil")
    assert figure(("oil", "tin"), 1, "en", TYPES, UNITS) == ("1 tin", "Oil")
    # ईंट is counted, not measured: "551 ईंट", never "551 count ईंट".
    assert figure(("brick", "count"), 551, "hi", TYPES, UNITS) == ("551", "ईंट")
    assert figure(("cash", "inr"), 233206, "hi", TYPES, UNITS) == ("₹2,33,206", "नगद")


@pytest.mark.parametrize("n,want", [(900, "900"), (1923, "1,923"),
                                    (150900, "1,50,900"), (233206, "2,33,206")])
def test_indian_grouping_is_what_the_site_renders(n, want):
    assert indian_grouping(n) == want
