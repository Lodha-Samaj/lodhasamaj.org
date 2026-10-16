"""Drift guard: the home page's festival list and the कार्यक्रम cards are static
markup duplicating data/events.json. When next year's dates are entered in one
place and not the other, these tests fail.

Comparison is per card, not per file: dates are substrings of one another
("24 अक्टूबर, रात्रि 8 बजे" sits inside "15–24 अक्टूबर, रात्रि 8 बजे") and all
events share one venue, so a whole-file search cannot see a single card drifting."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))["events"]


def source(page: str) -> str:
    raw = (ROOT / page).read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", raw, flags=re.S)


def text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def fest_blocks(page: str) -> list[str]:
    """The raw <li class="fest"> blocks, for checks that read a whole entry."""
    return re.findall(r'<li class="fest">(.*?)</li>', source(page), flags=re.S)


def fest_entries(page: str) -> list[dict[str, str]]:
    """One dict per hero entry. Each field is read from its own element, so a
    single drifted date fails on that event rather than hiding in a joined string."""
    entries = []
    for block in fest_blocks(page):
        when = re.search(r'<p class="fest-when">(.*?)</p>', block, flags=re.S)
        name = re.search(r'<p class="fest-name">(.*?)</p>', block, flags=re.S)
        assert when and name, f"hero entry in {page} is missing when/name: {block!r}"
        entries.append({"when": text(when.group(1)), "name": text(name.group(1))})
    return entries


def assert_single_shared_venue() -> str:
    """The hero states the venue once, below the list, because every event shares
    it. A second venue in events.json makes this fail, and the venue then has to
    move back into each entry."""
    venues = {e["where"] for e in EVENTS}
    assert len(venues) == 1, (
        f"events.json now has {len(venues)} venues {sorted(venues)}; the home hero "
        "states one shared venue and can no longer represent them")
    return venues.pop()





def test_home_has_exactly_one_festival_entry_per_event_with_its_own_fields():
    entries = fest_entries("hi/index.html")
    assert len(entries) == len(EVENTS)
    for event, entry in zip(EVENTS, entries):
        assert entry["name"] == event["titleHi"], (
            f"home entry name differs from data/events.json: {entry['name']!r}")
        assert entry["when"] == event["when"], (
            f"home entry date for {event['titleHi']!r} differs from data/events.json: {entry['when']!r}")


def test_home_states_the_shared_venue_from_events_json():
    assert assert_single_shared_venue() in element("hi/index.html", r'<p class="fest-where">(.*?)</p>')


def test_karyakram_has_exactly_one_entry_per_event_with_its_own_fields():
    entries = fest_entries("hi/karyakram/index.html")
    assert len(entries) == len(EVENTS)
    for event, entry in zip(EVENTS, entries):
        assert entry["name"] == event["titleHi"], entry
        assert entry["when"] == event["when"], entry


def test_karyakram_states_the_shared_venue_from_events_json():
    assert assert_single_shared_venue() in element(
        "hi/karyakram/index.html", r'<p class="fest-where">(.*?)</p>')


def home_cards(page: str) -> dict:
    """{"2026": "2026 44 दानदाता 46वां विशाल भंडारा …"} - the home register's line for
    each नवदुर्गा year. tools/update_home_stats.py writes them."""
    out = {}
    for line in re.findall(r'<li class="ly.*?</li>', source(page), flags=re.S):
        year = re.search(r'navdurga-mahotsav-(\d{4})/', line)
        if year:
            out[year.group(1)] = " ".join(re.sub(r"<[^>]+>", " ", line).split())
    return out


def element(page: str, pattern: str) -> str:
    match = re.search(pattern, source(page), flags=re.S)
    assert match, f"{pattern} not found in {page}"
    return text(match.group(1))


def ordinal_event():
    return next(e for e in EVENTS if "ordinal" in e)


def test_ordinals_match_in_the_home_hero():
    o = ordinal_event()["ordinal"]
    hero = element("hi/index.html", r'<section class="hero">(.*?)</section>')
    assert f"{o['bhandara']}वां विशाल भंडारा" in hero
    assert f"{o['kanyaPujan']}वां नगर कन्या पूजन" in hero


def test_the_home_card_for_this_year_counts_the_same_bhandara_as_the_hero():
    """The hero announces this year's भंडारा out of events.json; the card under it
    reports the donors of that same भंडारा, and its ordinal comes from the donor
    file. Two files, one number - this is where they are made to agree. The year
    before it is one ordinal back, because the भंडारा is held every year."""
    o = ordinal_event()["ordinal"]
    cards = home_cards("hi/index.html")
    this_year = max(cards)                     # the newest list on the page
    assert f"{o['bhandara']}वां विशाल भंडारा" in cards[this_year], cards[this_year]
    assert f"{o['kanyaPujan']}वां नगर कन्या पूजन" in cards[this_year], cards[this_year]
    earlier = cards.get(str(int(this_year) - 1), "")
    for number in re.findall(r"(\d+)वां\s+विशाल भंडारा", earlier):
        assert int(number) == o["bhandara"] - 1, earlier
    for number in re.findall(r"(\d+)वां\s+नगर कन्या पूजन", earlier):
        assert int(number) == o["kanyaPujan"] - 1, earlier


def test_ordinals_match_on_the_karyakram_entry():
    o = ordinal_event()["ordinal"]
    block = next(text(b) for b in fest_blocks("hi/karyakram/index.html")
                 if ordinal_event()["titleHi"] in b)
    assert f"{o['bhandara']}वां विशाल भंडारा" in block
    assert f"{o['kanyaPujan']}वां नगर कन्या पूजन" in block


# ---- English mirror -------------------------------------------------------
# events.json holds Hindi `when`/`where` and an English title only. The English
# pages are a fourth copy of the data, so derive the English wording from the
# Hindi fields through a fixed, tiny vocabulary. A new month, time word or venue
# makes the conversion raise KeyError/AssertionError rather than pass silently.
PLACES = {"महाराणा प्रताप चौराहा, महूनाका इंदौर": "Maharana Pratap Chauraha, Mhow Naka, Indore"}


def when_en(when: str) -> str:
    m = re.fullmatch(r"([\d–]+) अक्टूबर, (रात्रि|शाम) (\d+) बजे", when)
    assert m, f"unrecognised 'when' format: {when!r}"
    return f"{m.group(1)} October, {m.group(3)} pm"   # both रात्रि and शाम are evening


def ordinal_en(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def en_venue() -> str:
    return PLACES[assert_single_shared_venue()]





def test_english_home_has_one_festival_entry_per_event_with_its_own_fields():
    entries = fest_entries("en/index.html")
    assert len(entries) == len(EVENTS)
    for event, entry in zip(EVENTS, entries):
        assert entry["name"] == event["titleEn"], (
            f"English home entry name differs from data/events.json: {entry['name']!r}")
        assert entry["when"] == when_en(event["when"]), (
            f"English home entry date for {event['titleEn']!r} differs from "
            f"data/events.json: {entry['when']!r}")


def test_english_home_states_the_shared_venue_from_events_json():
    assert en_venue() in element("en/index.html", r'<p class="fest-where">(.*?)</p>')


def test_english_karyakram_has_one_entry_per_event_with_its_own_fields():
    entries = fest_entries("en/karyakram/index.html")
    assert len(entries) == len(EVENTS)
    for event, entry in zip(EVENTS, entries):
        assert entry["name"] == event["titleEn"], entry
        assert entry["when"] == when_en(event["when"]), entry


def test_english_karyakram_states_the_shared_venue_from_events_json():
    assert en_venue() in element("en/karyakram/index.html",
                                 r'<p class="fest-where">(.*?)</p>')


def test_english_ordinals_match_in_hero_stats_and_card():
    o = ordinal_event()["ordinal"]
    bhandara = f"{ordinal_en(o['bhandara'])} Vishal Bhandara"
    kanya = f"{ordinal_en(o['kanyaPujan'])} Nagar Kanya Pujan"
    hero = element("en/index.html", r'<section class="hero">(.*?)</section>')
    cards = home_cards("en/index.html")
    this_year = max(cards)
    block = next(text(b) for b in fest_blocks("en/karyakram/index.html")
                 if ordinal_event()["titleEn"] in b)
    assert bhandara in hero and kanya in hero
    # As in Hindi: this year's card reports this year's भंडारा, the one before it
    # is one ordinal back.
    assert bhandara in cards[this_year] and kanya in cards[this_year], cards[this_year]
    earlier = cards.get(str(int(this_year) - 1), "")
    for number in re.findall(r"(\d+)(?:st|nd|rd|th)\s+Nagar Kanya Pujan", earlier):
        assert int(number) == o["kanyaPujan"] - 1
    assert bhandara in block and kanya in block


def test_no_page_still_warns_that_the_dates_are_unconfirmed():
    """The समाज confirmed the 2026 dates, so the warning must be gone - from the
    pages and from events.json, which is the publish gate's own flag. If a later
    year is entered before the समाज has confirmed it, put the note back and turn
    the flag on again; this test then has to be turned around with it."""
    assert json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8")
                      )["needsConfirmation"] is False
    for page in ("hi/index.html", "hi/karyakram/index.html",
                 "en/index.html", "en/karyakram/index.html"):
        assert "date-note" not in source(page), page


# en/parichay carries one REVIEW comment more than hi/parichay: the check of the
# romanised spellings of historical names (Rao Jujhar Singh, Mankehni, Krishna Bai, Gopal Mahto).
# Hindi has no such comment because it has no romanisation. Every other page must match exactly.
EXTRA_EN_REVIEWS = {"parichay/": 1}


def test_review_comments_have_parity_between_hindi_and_english():
    for slug in assert_same_pages():
        hi = ROOT / "hi" / slug / "index.html"
        n_hi = len(re.findall(r"<!--.*?REVIEW.*?-->", hi.read_text(encoding="utf-8"), flags=re.S))
        en = (ROOT / "en" / slug / "index.html").read_text(encoding="utf-8")
        n_en = len(re.findall(r"<!--.*?REVIEW.*?-->", en, flags=re.S))
        assert n_en == n_hi + EXTRA_EN_REVIEWS.get(slug, 0), (
            f"/{slug}: {n_hi} REVIEW comment(s) in Hindi, {n_en} in English")


def page_slugs(lang: str) -> set[str]:
    """Slugs of every page under hi/ or en/ ('' is the home page)."""
    base = ROOT / lang
    slugs = set()
    for f in base.rglob("index.html"):
        rel = f.parent.relative_to(base).as_posix()
        slugs.add("" if rel == "." else rel + "/")
    return slugs


def assert_same_pages():
    """Hindi and English must offer the same pages. Comparing the two sets (not iterating
    one side) fails on an empty glob and on a page that exists in only one language."""
    hi, en = page_slugs("hi"), page_slugs("en")
    assert hi, "no pages found under hi/ - wrong working directory or hi/ emptied?"
    assert hi == en, (f"only in hi/: {sorted(hi - en)}; only in en/: {sorted(en - hi)}")
    return sorted(hi)


def test_every_hindi_page_has_a_reciprocal_english_page():
    for slug in assert_same_pages():
        hi, en = ROOT / "hi" / slug / "index.html", ROOT / "en" / slug / "index.html"
        hi_src, en_src = source(f"hi/{slug}index.html"), source(f"en/{slug}index.html")
        # href may be root-relative (before the domain sweep) or absolute (after)
        assert re.search(rf'hreflang="en" href="(https://[^/"]+)?/en/{slug}"', hi_src), hi
        assert re.search(rf'hreflang="hi" href="(https://[^/"]+)?/hi/{slug}"', en_src), en
        assert '<html lang="en">' in en_src
        assert "<form" not in en_src.lower()
