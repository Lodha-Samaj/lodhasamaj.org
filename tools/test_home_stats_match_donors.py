"""Drift guard: the figures in the home page's line of account are typed into
the HTML by hand, but they describe data/donors-2026.json - the list the समाज
is collecting now. When that list grows and the home page is not updated,
these tests fail.

The donor count, the flour total and the cash total are each checked on their
own, so one stale figure cannot hide behind two correct ones. Flour, because
the band reports the largest kind the year has brought in; if another kind
overtakes it the band should follow, and this test says so.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YEAR = 2026
DONORS = json.loads((ROOT / "data" / f"donors-{YEAR}.json").read_text(encoding="utf-8"))["donors"]


def indian_grouping(n: int) -> str:
    """1,50,900 - last three digits, then pairs. Matches formatTotal in donors-core.js."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def total(kind: str) -> int:
    return sum(item.get("qty", 0) for donor in DONORS for item in donor["items"]
               if item["type"] == kind and item.get("unit") in {"kg", "inr"})


def stats_text(page: str) -> str:
    src = (ROOT / page).read_text(encoding="utf-8")
    match = re.search(r'<section class="stats">(.*?)</section>', src, flags=re.S)
    assert match, f"no stats band in {page}"
    return " ".join(re.sub(r"<[^>]+>", " ", match.group(1)).split())


PAGES = ["hi/index.html", "en/index.html"]


def test_donor_count_matches_the_donor_list():
    for page in PAGES:
        assert str(len(DONORS)) in stats_text(page), (
            f"{page}: the stats band does not carry the donor count {len(DONORS)} "
            f"from donors-{YEAR}.json")


def test_the_band_reports_the_largest_kind_that_year_received():
    goods = {kind: total(kind) for kind in ("flour", "sugar", "mawa", "salt")}
    largest = max(goods, key=goods.get)
    assert largest == "flour", (
        f"{largest} has overtaken flour in donors-{YEAR}.json - the band should "
        f"report it instead")
    want = indian_grouping(goods[largest])
    for page in PAGES:
        assert want in stats_text(page), (
            f"{page}: the stats band does not carry the flour total {want} kg")


def test_cash_total_matches_the_donor_list():
    want = indian_grouping(total("cash"))
    for page in PAGES:
        assert want in stats_text(page), (
            f"{page}: the stats band does not carry the cash total ₹{want}")


def test_indian_grouping_is_what_the_site_renders():
    # donors-core.js formatTotal produces these; if that changes, this guard
    # would start comparing against the wrong shape of number.
    assert indian_grouping(900) == "900"
    assert indian_grouping(1923) == "1,923"
    assert indian_grouping(47305) == "47,305"
    assert indian_grouping(150900) == "1,50,900"
    assert indian_grouping(233206) == "2,33,206"
