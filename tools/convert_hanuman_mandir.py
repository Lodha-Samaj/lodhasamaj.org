#!/usr/bin/env python3
"""Build data/hanuman-mandir.json from the समाज's श्री हनुमान मंदिर निर्माण list.

This is a campaign, not a नवरात्र year: building materials (ईंट, सीमेंट,
सरिया) as well as cash, and no year. The page reads it through
`data-list="hanuman-mandir"` rather than `data-year`.

The source notes against many entries that the gift has been received
("नकद प्राप्त", "ऑनलाइन प्राप्त", "सामग्री प्राप्त"). That is the समाज's own
record of who has paid. The public page does not show it, and since every file
under data/ is published, it is dropped here rather than carried in the JSON.

As in the yearly converters, parsing is strict (a word it cannot account for is
an error, not a silent drop), the two entries stated in prose are held in
OVERRIDES against their exact source text, and nothing infers who has died:
every स्वर्गीय name is printed for the समाज to rule on.

    python3 tools/convert_hanuman_mandir.py [--check]
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from convert_2025_md import DEATH_MARKER, clean_name

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/d-data/Data/Lodha-Samaj-2025/"
              "Lodha-Samaj-Shri-Hanuman-Temple-Construction-Work.txt")
OUT = ROOT / "data" / "hanuman-mandir.json"

LIST = "hanuman-mandir"
TITLE = {"hi": "श्री हनुमान मंदिर निर्माण", "en": "Shri Hanuman Temple Construction"}
SUBTITLE = {"hi": "लोधा कॉलोनी, महू नाका, इंदौर", "en": "Lodha Colony, Mhow Naka, Indore"}

ENTRY = re.compile(r"^(\d+)\.\s+(.*)$")
# The name is the bold part, optionally followed by a role in brackets. A dash
# inside the bold ("गुप्त दान — जय श्री राम") belongs to the name.
LINE = re.compile(r"^\*\*(.+?)\*\*\s*(\([^)]*\))?\s*—\s*(.+)$")
RECEIPT = re.compile(r"(?:\s+(?:नकद|ऑनलाइन)\s+प्राप्त|,\s*सामग्री\s+प्राप्त)$")
ITEM_SPLIT = re.compile(r",\s+")
MONEY = re.compile(r"^₹\s*(\d{1,3}(?:,\d{2})*(?:,\d{3})?|\d+)$")
QTY = re.compile(r"^(\d+)\s+(.*)$")

TYPE_WORDS = {"सीमेंट": "cement", "ईंट": "brick", "सरिया": "rebar"}
UNIT_WORDS = {"बोरी": "bag", "किलोग्राम": "kg", "किलो": "kg"}
# Bricks are counted bare ("551 ईंट"); the type label names the thing.
DEFAULT_UNIT = {"brick": "count"}

# number -> (exact source text it was ruled against, items)
OVERRIDES = {
    30: ("**श्री मन्नूलाल जी वर्मा** — श्री हनुमान मंदिर प्रांगण में संपूर्ण टाइल्स लगाने का सहयोग",
         [{"type": "tiles", "note": "मंदिर प्रांगण में संपूर्ण"}]),
    35: ("**स्वर्गीय श्री रमेश जी जाट (श्री बादशाह बाबा)** — श्री हनुमान मंदिर प्रांगण हेतु छत का पंखा",
         [{"type": "fan", "note": "मंदिर प्रांगण हेतु"}]),
}


def parse_items(text: str, number: int) -> list[dict]:
    items = []
    for seg in (s.strip() for s in ITEM_SPLIT.split(text.strip())):
        money = MONEY.match(seg)
        if money:
            items.append({"type": "cash", "qty": int(money.group(1).replace(",", "")),
                          "unit": "inr"})
            continue
        q = QTY.match(seg)
        if not q:
            raise ValueError(f"#{number}: {seg!r} states no quantity")
        qty, rest = int(q.group(1)), q.group(2)
        code = unit = None
        leftover = []
        for word in rest.split():
            if word in TYPE_WORDS and code is None:
                code = TYPE_WORDS[word]
            elif word in UNIT_WORDS and unit is None:
                unit = UNIT_WORDS[word]
            else:
                leftover.append(word)
        if code is None:
            raise ValueError(f"#{number}: {seg!r} names no item type")
        if leftover:
            raise ValueError(f"#{number}: {seg!r} has words this script cannot "
                             f"account for: {leftover}")
        unit = unit or DEFAULT_UNIT.get(code)
        if not unit:
            raise ValueError(f"#{number}: {seg!r} gives a quantity but names no "
                             f"unit, so it would be left out of the totals")
        items.append({"type": code, "qty": qty, "unit": unit})
    if not items:
        raise ValueError(f"#{number}: no contribution found")
    return items


def split_line(text: str, number: int) -> tuple[str, str]:
    m = LINE.match(text)
    if not m:
        raise ValueError(f"#{number}: {text!r} is not '**name** (role) — gift'")
    bold, role, rest = m.groups()
    name = clean_name(f"{bold} {role}" if role else bold)
    return name, RECEIPT.sub("", rest.strip())


def parse_line(text: str, number: int) -> dict:
    name, rest = split_line(text, number)
    return {"name": {"hi": name}, "items": parse_items(rest, number)}


def read_rows(text: str) -> list[tuple[int, str]]:
    rows = []
    for line in text.splitlines():
        m = ENTRY.match(line.strip())
        if m:
            rows.append((int(m.group(1)), unicodedata.normalize("NFC", m.group(2).strip())))
    return rows


def build(rows) -> tuple[list[dict], list[str]]:
    numbers = [n for n, _ in rows]
    expected = list(range(1, len(rows) + 1))
    if numbers != expected:
        raise ValueError(f"entries are not numbered 1..{len(rows)} without gaps: "
                         f"{sorted(set(expected) ^ set(numbers))}")
    donors, death_marked = [], []
    for number, text in rows:
        override = OVERRIDES.get(number)
        if override:
            ruled_against, items = override
            if text != unicodedata.normalize("NFC", ruled_against):
                raise ValueError(
                    f"#{number} has an OVERRIDES entry written against\n"
                    f"    {ruled_against!r}\n  but the source now reads\n"
                    f"    {text!r}\n  Re-review that ruling before importing.")
            name, _ = split_line(text, number)
            donor = {"name": {"hi": name}, "items": [dict(i) for i in items]}
        else:
            donor = parse_line(text, number)
        if DEATH_MARKER.match(donor["name"]["hi"]):
            death_marked.append(f"  #{number}: {donor['name']['hi']}")
        donors.append(donor)
    return donors, death_marked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="parse and report, write nothing")
    args = ap.parse_args()

    rows = read_rows(SOURCE.read_text(encoding="utf-8"))
    try:
        donors, death_marked = build(rows)
    except ValueError as exc:
        print(f"FAILED: {exc}")
        return 1

    print(f"{len(rows)} entries in the source -> {len(donors)} donors")
    if death_marked:
        print(f"\nstarting with स्वर्गीय, NOT flagged, awaiting the समाज's review "
              f"({len(death_marked)}):")
        print("\n".join(death_marked))
    if args.check:
        print("\n--check: nothing written")
        return 0
    payload = {"list": LIST, "title": TITLE, "subtitle": SUBTITLE, "donors": donors}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
