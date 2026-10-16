"""The home page's cards are generated; these tests keep them honest.

A list that changes without tools/update_home_stats.py being re-run leaves the
home page claiming yesterday's figures, so --check runs here. The rest guard
the arithmetic and the labels the cards are built from.
"""
import json
import re
from pathlib import Path

import pytest

from update_home_stats import (ROOT, _labels, block, figure, indian_grouping,
                               lists_in_order, main, totals)

INDEX = json.loads((ROOT / "data" / "donors-index.json").read_text(encoding="utf-8"))
TYPES, UNITS = _labels("TYPE_LABELS"), _labels("UNIT_LABELS")


def test_the_home_pages_carry_the_current_figures():
    assert main(["--check"]) == 0, (
        "the home page cards are stale - run python3 tools/update_home_stats.py")


def test_every_list_in_the_index_gets_a_card():
    keys = [row["key"] for row in lists_in_order(INDEX)]
    assert sorted(keys) == sorted([str(y) for y in INDEX["years"]] + INDEX["lists"])
    # Newest first, and a year's महोत्सव before that year's यात्रा.
    assert keys[0] == str(max(INDEX["years"]))
    assert keys.index("2026") < keys.index("kavad-yatra-2026") < keys.index("2025")
    assert keys[-1] == "hanuman-mandir"


def test_a_cards_figures_are_the_lists_own_totals():
    year = max(INDEX["years"])
    donors = json.loads((ROOT / "data" / f"donors-{year}.json").read_text(encoding="utf-8"))["donors"]
    cash = totals(donors)[("cash", "inr")]
    html = block("hi", INDEX, TYPES, UNITS)
    card = html[html.index(f"navdurga-mahotsav-{year}"):]
    card = card[:card.index("</li>")]
    assert f"₹{indian_grouping(int(cash))}" in card
    assert f"{len(donors)} दानदाता" in card


def test_cash_leads_a_card_and_then_the_largest_quantities():
    html = block("hi", INDEX, TYPES, UNITS)
    card = html[html.index("hanuman-mandir"):]
    card = card[:card.index("</ul>")]
    figures = re.findall(r"<b>([^<]+)</b> <span>([^<]+)</span>", card)
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
