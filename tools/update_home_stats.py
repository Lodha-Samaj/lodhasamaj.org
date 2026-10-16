#!/usr/bin/env python3
"""Write the home page's line of account: one card per donor list.

The home page used to carry one year's three figures, typed by hand, and three
hand-picked donors beside them. Now every list the समाज keeps - each नवदुर्गा
महोत्सव, each कावड़ यात्रा, the मंदिर - gets its own card with what that list
actually received. The numbers are written into the HTML here rather than
fetched by the browser, so the page opens with them and shows them with
JavaScript turned off.

The labels are read out of assets/js/donors-core.js, never copied: the cards
must say "1,174 किलो आटा" exactly as the दान page says it.

    python3 tools/update_home_stats.py [--check]

tools/test_update_home_stats.py runs --check, so a list that changes without
this script being re-run fails the suite.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORE = ROOT / "assets" / "js" / "donors-core.js"
PAGES = {"hi": ROOT / "hi" / "index.html", "en": ROOT / "en" / "index.html"}

START = "<!-- tally:start -->"
END = "<!-- tally:end -->"

# A year's list is the नवदुर्गा महोत्सव's; the same wording as the donor history.
YEAR_TITLE = {"hi": lambda y: f"नवदुर्गा महोत्सव एवं विशाल भंडारा {y}",
              "en": lambda y: f"Navdurga Mahotsav and Vishal Bhandara {y}"}
YEAR_URL = {"hi": lambda y: f"/hi/daan/navdurga-mahotsav-{y}/",
            "en": lambda y: f"/en/daan/navdurga-mahotsav-{y}/"}
DONORS_WORD = {"hi": "दानदाता", "en": ("donor", "donors")}
# The दान page's three colours: the मंदिर indigo, the यात्रा red, the महोत्सव gold.
ACCENT = {"mandir": "give-temple", "yatra": "give-yatra", "festival": "give-festival"}
LEAD = {"hi": ("हर आयोजन का हिसाब", "सभी सूचियाँ",
               'हर सूची उसी आयोजन की है। पूरी सूची और खोज <a href="/hi/daan/">दान पृष्ठ</a> पर है।'),
        "en": ("What each event received", "All lists",
               'Each card is one list. The full lists, with search, are on the '
               '<a href="/en/daan/">donations page</a>.')}


def _labels(name: str) -> dict:
    """TYPE_LABELS / UNIT_LABELS out of donors-core.js, so the two cannot drift."""
    src = CORE.read_text(encoding="utf-8")
    body = re.search(rf"export const {name} = {{(.*?)^}};", src, flags=re.S | re.M)
    if not body:
        raise SystemExit(f"{CORE.name}: no {name} to read")
    out = {}
    for code, fields in re.findall(r"^\s*(\w+):\s*{([^}]*)}", body.group(1), flags=re.M):
        out[code] = {k: v for k, v in re.findall(r"(\w+):\s*'([^']*)'", fields)}
    return out


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


def ordinal_en(n: int) -> str:
    """46 -> 46th. The same rule as ordinal() in donors-core.js."""
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def festival_heading(festival, lang: str) -> list[str]:
    """["46वां विशाल भंडारा", "23वां नगर कन्या पूजन"] - festivalHeading in Python."""
    f = festival or {}
    if lang == "hi":
        return [f"{f[k]}वां {word}" for k, word in
                (("bhandara", "विशाल भंडारा"), ("kanyaPujan", "नगर कन्या पूजन")) if f.get(k)]
    return [f"{ordinal_en(f[k])} {word}" for k, word in
            (("bhandara", "Vishal Bhandara"), ("kanyaPujan", "Nagar Kanya Pujan")) if f.get(k)]


def totals(donors: list) -> dict:
    """{(type, unit): quantity} over one list, counting only numeric quantities."""
    out = {}
    for donor in donors:
        for item in donor.get("items", []):
            qty = item.get("qty")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)):
                continue
            key = (item["type"], item.get("unit"))
            out[key] = out.get(key, 0) + qty
    return out


def figure(key, qty, lang, types, units) -> tuple[str, str]:
    """("₹47,305", "नगद") / ("1,174 किलो", "आटा") - the number, then what it was."""
    kind, unit = key
    label = types.get(kind, {}).get(lang, kind)
    if unit == "inr":
        return f"₹{indian_grouping(int(qty))}", label
    u = units.get(unit, {})
    word = u.get("enPlural") if lang == "en" and u.get("enPlural") and qty != 1 else u.get(lang, "")
    amount = f"{indian_grouping(int(qty))}" if float(qty).is_integer() else f"{qty}"
    return f"{amount} {word}".strip(), label


def lists_in_order(index: dict) -> list[dict]:
    """Newest first: a year's महोत्सव, then that year's यात्रा; the मंदिर last."""
    rows = []
    for year in sorted(index["years"], reverse=True):
        rows.append({"key": str(year), "year": year, "kind": "festival"})
        for slug in index["lists"]:
            if slug.endswith(f"-{year}"):
                rows.append({"key": slug, "year": year, "kind": "yatra"})
    for slug in index["lists"]:
        if not any(r["key"] == slug for r in rows):
            rows.append({"key": slug, "year": None, "kind": "mandir"})
    return rows


def card(row: dict, lang: str, types: dict, units: dict) -> str:
    key = row["key"]
    path = DATA / (f"donors-{key}.json" if row["year"] and key.isdigit() else f"{key}.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    donors = data["donors"]
    if key.isdigit():
        title, url = YEAR_TITLE[lang](key), YEAR_URL[lang](key)
    else:
        title = data["title"].get(lang) or data["title"]["hi"]
        url = f"/{lang}/daan/{key}/"
    n = len(donors)
    who = f"{n} {DONORS_WORD['hi']}" if lang == "hi" else \
          f"{n} {DONORS_WORD['en'][0] if n == 1 else DONORS_WORD['en'][1]}"
    # A नवदुर्गा list counts its भंडारा and its कन्या पूजन; the card says which
    # ones it is reporting, in the same words as that list's own page.
    who = " · ".join([who, *filter(None, festival_heading(data.get("festival"), lang))])
    ranked = sorted(totals(donors).items(), key=lambda kv: (kv[0][0] != "cash", -kv[1]))
    rows = "".join(
        f'\n          <li><b>{amount}</b> <span>{label}</span></li>'
        for amount, label in (figure(k, q, lang, types, units) for k, q in ranked[:4]))
    hi_only = ' lang="hi"' if lang == "en" else ""
    return (f'      <li class="tally {ACCENT[row["kind"]]}">\n'
            f'        <h3><a href="{url}"{hi_only}>{title}</a></h3>\n'
            f'        <p class="tally-who">{who}</p>\n'
            f'        <ul class="tally-rows">{rows}\n        </ul>\n'
            f'      </li>\n')


def block(lang: str, index: dict, types: dict, units: dict) -> str:
    heading, all_text, note = LEAD[lang]
    cards = "".join(card(row, lang, types, units) for row in lists_in_order(index))
    return (f'{START}\n'
            f'    <div class="wrap section">\n'
            f'      <div class="section-head">\n'
            f'        <h2>{heading}</h2>\n'
            f'        <a class="all" href="/{lang}/daan/">{all_text}</a>\n'
            f'      </div>\n'
            f'      <ul class="tally-grid">\n{cards}      </ul>\n'
            f'      <p class="stats-note">{note}</p>\n'
            f'    </div>\n'
            f'    {END}')


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report whether the pages are current; change nothing")
    args = parser.parse_args(argv)

    index = json.loads((DATA / "donors-index.json").read_text(encoding="utf-8"))
    types, units = _labels("TYPE_LABELS"), _labels("UNIT_LABELS")
    stale = []
    for lang, page in PAGES.items():
        src = page.read_text(encoding="utf-8")
        if START not in src or END not in src:
            print(f"{page.relative_to(ROOT)}: no {START} … {END} block to write into")
            return 1
        fresh = block(lang, index, types, units)
        current = src[src.index(START):src.index(END) + len(END)]
        if current == fresh:
            continue
        stale.append(page)
        if not args.check:
            page.write_text(src.replace(current, fresh), encoding="utf-8")
    if not stale:
        print("home pages: the account of every list is current")
        return 0
    names = ", ".join(str(p.relative_to(ROOT)) for p in stale)
    if args.check:
        print(f"stale: {names} - run python3 tools/update_home_stats.py")
        return 1
    print(f"written: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
