#!/usr/bin/env python3
"""Write each आयोजन's figures into the दान page, the way the home band reads.

The दान page named three आयोजन and then listed their years, but never said
what any of them received. Under each heading there is now a short sheet: one
line per year - how many gave, the cash, and the two kinds that आयोजन is
mostly given. The नवदुर्गा महोत्सव and the कावड़ यात्रा show 2026 and 2025; the
मंदिर has no years, so it shows one line, अब तक.

The figures are written into the HTML rather than fetched, so the page opens
with them and keeps them with JavaScript off. Labels come from
assets/js/donors-core.js, never copied, so a sheet cannot say "किलो" where the
list says something else.

    python3 tools/update_daan_stats.py [--check]

tools/test_update_daan_stats.py runs --check: edit a list without re-running
this and the suite says so.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CORE = ROOT / "assets" / "js" / "donors-core.js"
PAGES = {"hi": ROOT / "hi" / "daan" / "index.html", "en": ROOT / "en" / "daan" / "index.html"}

# Each आयोजन's card on the दान page, the lists it shows, and how many years of
# them. A year list is named by its year; a campaign by its slug.
CARDS = [
    {"slug": "temple", "lists": ["hanuman-mandir"]},
    {"slug": "yatra", "lists": ["kavad-yatra-2026", "kavad-yatra-2025"]},
    {"slug": "festival", "lists": ["2026", "2025"]},
]
SO_FAR = {"hi": "अब तक", "en": "so far"}
DONORS_WORD = {"hi": "दानदाता", "en": ("donor", "donors")}


def _labels(name: str) -> dict:
    """TYPE_LABELS / UNIT_LABELS out of donors-core.js, so the two cannot drift."""
    src = CORE.read_text(encoding="utf-8")
    body = re.search(rf"export const {name} = {{(.*?)^}};", src, flags=re.S | re.M)
    if not body:
        raise SystemExit(f"{CORE.name}: no {name} to read")
    return {code: dict(re.findall(r"(\w+):\s*'([^']*)'", fields))
            for code, fields in re.findall(r"^\s*(\w+):\s*{([^}]*)}", body.group(1), flags=re.M)}


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


def read_list(key: str) -> dict:
    path = DATA / (f"donors-{key}.json" if key.isdigit() else f"{key}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def totals(donors: list) -> dict:
    """{(type, unit): quantity}, counting only numeric quantities."""
    out = {}
    for donor in donors:
        for item in donor.get("items", []):
            qty = item.get("qty")
            if isinstance(qty, bool) or not isinstance(qty, (int, float)):
                continue
            key = (item["type"], item.get("unit"))
            out[key] = out.get(key, 0) + qty
    return out


def goods_columns(card: dict, how_many: int = 2) -> list[str]:
    """The kinds this आयोजन is mostly given, cash aside.

    Counted first by how many of its lists brought that kind, then by how much:
    a kind one year happened to bring should not push out one that comes every
    year, because the lines are read against each other.
    """
    weight, seen = {}, {}
    for key in card["lists"]:
        kinds = set()
        for (kind, _unit), qty in totals(read_list(key)["donors"]).items():
            if kind == "cash":
                continue
            weight[kind] = weight.get(kind, 0) + qty
            kinds.add(kind)
        for kind in kinds:
            seen[kind] = seen.get(kind, 0) + 1
    return sorted(weight, key=lambda k: (-seen[k], -weight[k]))[:how_many]


def amount(key, qty, lang, types, units) -> tuple[str, str]:
    """("₹47,305", "नगद") / ("1,174 किलो", "आटा") - the figure, then what it was."""
    kind, unit = key
    label = types.get(kind, {}).get(lang, kind)
    if unit == "inr":
        return f"₹{indian_grouping(int(qty))}", label
    u = units.get(unit, {})
    word = u.get("enPlural") if lang == "en" and u.get("enPlural") and qty != 1 else u.get(lang, "")
    figure = indian_grouping(int(qty)) if float(qty).is_integer() else str(qty)
    return f"{figure} {word}".strip(), label


def stat(figure: str, label: str) -> str:
    return f'              <p class="stat"><b>{figure}</b><span>{label}</span></p>\n'


def row(key: str, card: dict, lang: str, types: dict, units: dict) -> str:
    data = read_list(key)
    donors = data["donors"]
    n = len(donors)
    who = DONORS_WORD["hi"] if lang == "hi" else \
        (DONORS_WORD["en"][0] if n == 1 else DONORS_WORD["en"][1])
    mine = totals(donors)
    cells = [stat(str(n), who)]
    cash = [(k, q) for k, q in mine.items() if k[0] == "cash"]
    if cash:
        cells.append(stat(*amount(*max(cash, key=lambda kv: kv[1]), lang, types, units)))
    for kind in card["goods"]:
        match = [(k, q) for k, q in mine.items() if k[0] == kind]
        if match:
            cells.append(stat(*amount(*max(match, key=lambda kv: kv[1]), lang, types, units)))
    # A year list is named by its year; a campaign's slug ends in one
    # ("kavad-yatra-2026"). Only a campaign with no year at all reads अब तक.
    year = re.search(r"(?:^|-)((?:19|20)\d{2})$", key)
    when = year.group(1) if year else SO_FAR[lang]
    return (f'            <div class="sheet-row">\n'
            f'              <h3>{when}</h3>\n{"".join(cells)}'
            f'            </div>\n')


def sheet(card: dict, lang: str, types: dict, units: dict) -> str:
    card = {**card, "goods": goods_columns(card)}
    rows = "".join(row(key, card, lang, types, units) for key in card["lists"])
    return (f'<!-- sheet:{card["slug"]} -->\n'
            f'          <div class="sheet">\n{rows}          </div>\n'
            f'          <!-- /sheet:{card["slug"]} -->')


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report whether the pages are current; change nothing")
    args = parser.parse_args(argv)

    types, units = _labels("TYPE_LABELS"), _labels("UNIT_LABELS")
    stale = []
    for lang, page in PAGES.items():
        src = page.read_text(encoding="utf-8")
        fresh_src = src
        for card in CARDS:
            start, end = f'<!-- sheet:{card["slug"]} -->', f'<!-- /sheet:{card["slug"]} -->'
            if start not in fresh_src or end not in fresh_src:
                print(f"{page.relative_to(ROOT)}: no {start} … {end} to write into")
                return 1
            current = fresh_src[fresh_src.index(start):fresh_src.index(end) + len(end)]
            fresh_src = fresh_src.replace(current, sheet(card, lang, types, units))
        if fresh_src == src:
            continue
        stale.append(page)
        if not args.check:
            page.write_text(fresh_src, encoding="utf-8")
    if not stale:
        print("दान page: every आयोजन's figures are current")
        return 0
    names = ", ".join(str(p.relative_to(ROOT)) for p in stale)
    if args.check:
        print(f"stale: {names} - run python3 tools/update_daan_stats.py")
        return 1
    print(f"written: {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
