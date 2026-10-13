#!/usr/bin/env python3
"""Build data/donors-2024.json from the समाज's markdown सहयोगकर्ता सूची for 2024.

The 2024 list is written differently from 2025: an em dash between the name and
the contribution, several items joined by commas rather than "+", plural units
("5 डब्बे तेल"), "गैस सिलेंडर" for gas, and money with Indian digit grouping
("₹1,000 नगद"). The name tidying, item vocabulary and death-marker rule are
shared with convert_2025_md.py so the two years read the same on the site.

As there, parsing is strict: a word it cannot account for is an error, not a
silent drop, and the one entry stated in prose is held in OVERRIDES against its
exact source text.

Nothing here infers who has died, and MEMORIAM is empty: no 2024 entry has
been hand-reviewed yet, so every death-marked name is printed for review.
Rows that repeat another row word for word are imported as written (the समाज
may have recorded two gifts) and printed for review too.

The source states no festival ordinals, so "festival" is left out rather than
counted back from 2025.

    python3 tools/convert_2024_md.py [--check]

Then, always: python3 tools/assign_donor_ids.py, which gives the rewritten
entries their Donor IDs back (the converter writes the list without them).
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from convert_2025_md import (DEATH_MARKER, DEFAULT_UNIT, FILLER, TYPE_WORDS,
                             UNIT_WORDS, clean_name)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/d-data/Data/Lodha-Samaj-2025/lodha_samaj_sahyogkarta_suchi_2024.md")
OUT = ROOT / "data" / "donors-2024.json"

YEAR = 2024

ENTRY = re.compile(r"^(\d+)\.\s+(.*)$")
SEP = re.compile(r"\s+—\s+")
# Split items on a comma followed by a space; "₹1,000" has none.
ITEM_SPLIT = re.compile(r",\s+")
MONEY = re.compile(r"^₹\s*(\d{1,3}(?:,\d{2})*(?:,\d{3})?|\d+)(?:\s+नगद)?$")
QTY = re.compile(r"^(\d+)\s+(.*)$")

# In 2025 "गैस" only decorated "गैस टंकी"; in 2024 it is the item itself.
TYPES_2024 = {**TYPE_WORDS, "गैस": "gas"}
UNITS_2024 = {**UNIT_WORDS, "डब्बे": "tin", "सिलेंडर": "cylinder"}
FILLER_2024 = FILLER - {"गैस"}

# number -> (exact source text it was ruled against, items)
OVERRIDES = {
    121: ("श्री मनोहर जी वर्मा एवं स्व. श्री दुलारे जी वर्मा (जलगांव) — भंडारे के लिए संपूर्ण केले के पत्ते",
          [{"type": "pattal", "note": "भंडारे के लिए संपूर्ण"}]),
}

MEMORIAM: dict[int, str] = {}


def parse_items(segment_text: str, number: int) -> list[dict]:
    items = []
    for seg in (s.strip() for s in ITEM_SPLIT.split(segment_text.strip())):
        if "*" in seg:
            raise ValueError(f"#{number}: {seg!r} carries an unexplained '*'")
        money = MONEY.match(seg)
        if money:
            items.append({"type": "cash", "qty": int(money.group(1).replace(",", "")),
                          "unit": "inr"})
            continue
        q = QTY.match(seg)
        if not q:
            raise ValueError(f"#{number}: {seg!r} states no quantity")
        if re.match(r"^\d", q.group(2)):
            raise ValueError(f"#{number}: {seg!r} runs two numbers together")
        qty, rest = int(q.group(1)), q.group(2)
        code = unit = None
        leftover = []
        for word in rest.split():
            if word in TYPES_2024 and code is None:
                code = TYPES_2024[word]
            elif word in UNITS_2024 and unit is None:
                unit = UNITS_2024[word]
            elif word not in FILLER_2024:
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


def read_source(path: Path = SOURCE) -> list[tuple[int, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ENTRY.match(line.strip())
        if m:
            rows.append((int(m.group(1)), unicodedata.normalize("NFC", m.group(2).strip())))
    return rows


def build(rows) -> tuple[list[dict], list[str], list[str]]:
    donors, death_marked = [], []
    seen_numbers = [n for n, _ in rows]
    expected = list(range(1, len(rows) + 1))
    if seen_numbers != expected:
        raise ValueError(f"entries are not numbered 1..{len(rows)} without gaps: "
                         f"{sorted(set(expected) ^ set(seen_numbers))}")

    by_text = defaultdict(list)
    for number, text in rows:
        by_text[text].append(number)
        if not SEP.search(text):
            raise ValueError(f"#{number}: {text!r} has no ' — ' between the "
                             f"name and the contribution")
        raw_name, raw_items = SEP.sub("\x00", text).rsplit("\x00", 1)
        name = clean_name(raw_name)
        override = OVERRIDES.get(number)
        if override:
            ruled_against, items = override
            if text != unicodedata.normalize("NFC", ruled_against):
                raise ValueError(
                    f"#{number} has an OVERRIDES entry written against\n"
                    f"    {ruled_against!r}\n  but the source now reads\n"
                    f"    {text!r}\n  Re-review that ruling before importing.")
            items = [dict(i) for i in items]
        else:
            items = parse_items(raw_items, number)

        donor = {"name": {"hi": name}}
        if number in MEMORIAM:
            donor["name"]["hi"] = MEMORIAM[number]
            donor["memoriam"] = True
        elif DEATH_MARKER.match(name):
            death_marked.append(f"  #{number}: {name}")
        donor["items"] = items
        donors.append(donor)

    repeats = [f"  #{' = #'.join(map(str, nums))}: {text}"
               for text, nums in by_text.items() if len(nums) > 1]
    return donors, death_marked, repeats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="parse and report, write nothing")
    args = ap.parse_args()

    rows = read_source()
    try:
        donors, death_marked, repeats = build(rows)
    except ValueError as exc:
        print(f"FAILED: {exc}")
        return 1

    print(f"{len(rows)} entries in the source -> {len(donors)} donors")
    if death_marked:
        print(f"\ndeath-marked names NOT flagged, awaiting the समाज's review "
              f"({len(death_marked)}):")
        print("\n".join(death_marked))
    if repeats:
        print(f"\nrows repeated word for word, imported as written, awaiting "
              f"review ({len(repeats)}):")
        print("\n".join(repeats))

    if args.check:
        print("\n--check: nothing written")
        return 0
    payload = {"year": YEAR, "donors": donors}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    print("Check data/donors-index.json lists 2024 and both year pages exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
