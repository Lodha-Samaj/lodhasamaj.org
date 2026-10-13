#!/usr/bin/env python3
"""Rebuild data/donors-2025.json from the समाज's markdown सहयोगकर्ता सूची.

This replaces convert_2025.py as the import path for 2025. That script read the
old website's HTML, which held 82 of the 166 entries; this markdown is the
समाज's own full list and contains every one of those 82.

Nothing here infers who has died. The स्व./स्व•/स्वर्गीय marker in this list
usually names an ancestor in whose memory a living family is giving, not the
donor, so MEMORIAM below is a hand-reviewed set and every other death-marked
entry is printed for review instead of being flagged.

Parsing is strict on purpose: a word it cannot account for is an error, not a
silent drop. Entries the source states in prose (or states wrongly) are listed
in OVERRIDES, each guarded by the exact source text it was written against, so
an edited source fails loudly instead of applying an old ruling to a new row.

    python3 tools/convert_2025_md.py [--check]

Then, always: python3 tools/assign_donor_ids.py, which gives the rewritten
entries their Donor IDs back (the converter writes the list without them).
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/d-data/Data/Lodha-Samaj-2025/lodha_samaj_sahyogkarta_suchi_2025.md")
OUT = ROOT / "data" / "donors-2025.json"

YEAR = 2025
FESTIVAL = {"bhandara": 45, "kanyaPujan": 22}

ENTRY = re.compile(r"^(\d+)\.\s+(.*)$")
# Names carry hyphens ("श्री राजू जी जाट-श्री मोहन जी जाट"), so the name/contribution
# split is on the LAST dash that has spaces around it.
SEP = re.compile(r"\s+[–-]\s+")
MONEY = re.compile(r"^₹?\s*([\d']+)\s*/?-?$")
QTY = re.compile(r"^(\d+)\s+(.*)$")
DEATH_MARKER = re.compile(r"^\s*(?:स्व\s*[.•]|स्वर्गीय|स्वर्ग\s)\s*")

TYPE_WORDS = {
    "शक्कर": "sugar", "आटा": "flour", "तेल": "oil", "नमक": "salt",
    "घी": "ghee", "मावा": "mawa", "पानी": "water", "नारियल": "coconut",
    "श्रीफल": "coconut", "बेसन": "besan", "रवा": "rava", "चावल": "rice",
    "पत्तल": "pattal", "टंकी": "gas",
}
UNIT_WORDS = {"किलो": "kg", "डब्बा": "tin", "जार": "jar",
              "नग": "piece", "छोटी": "cylinder"}
# Words that decorate a contribution without changing it.
FILLER = {"शुद्ध", "देसी", "के", "लिए", "हेतु", "कन्या", "पूजन", "गैस"}
# Types the source counts without naming a unit ("51 नारियल"). Anything else
# that arrives without a unit is an error, because it would silently drop out
# of the year's totals.
DEFAULT_UNIT = {"coconut": "piece"}

# number -> (exact source text it was ruled against, name override or None, items)
OVERRIDES = {
    20: ("श्री मनोहर जी वर्मा एवं स्व. श्री दुलारे जी वर्मा (महाराष्ट्र वाले) – सम्पूर्ण भंडारे हेतु केले के पत्तल",
         None, [{"type": "pattal", "note": "सम्पूर्ण भंडारे हेतु"}]),
    # The '*' in #36, #37 and #134 has no legend anywhere in the source.
    # REVIEW: ask the समाज what it marks; the amounts themselves are legible.
    36: ("श्री गुलाब जी जामदार – ₹7100 *",
         None, [{"type": "cash", "qty": 7100, "unit": "inr"}]),
    # Source reads "10 111 किलो शक्कर". Sachin confirmed 111 किलो; the leading
    # "10" is a typing slip.
    37: ("श्री अजय जी कोतुल एवं श्रीमती कुमकुम बाई – 10 111 किलो शक्कर *",
         None, [{"type": "sugar", "qty": 111, "unit": "kg"}]),
    77: ("श्री प्रेम जी जमदार-श्री आकाश जी चौधरी - कन्या पूजन हेतु संपूर्ण श्रीफल",
         None, [{"type": "coconut", "note": "कन्या पूजन हेतु संपूर्ण श्रीफल"}]),
    134: ("श्री जुगल जी कोतवाल - ₹2'100/- *",
          None, [{"type": "cash", "qty": 2100, "unit": "inr"}]),
    # Source has no separator and writes "1=डब्बा".
    # REVIEW: the समाज should fix this line in the source.
    135: ("स्व•श्री लड्डू भवानी बोस परिवार कि और से 1=डब्बा तेल,",
          "स्व. श्री लड्डू भवानी बोस परिवार कि ओर से",
          [{"type": "oil", "qty": 1, "unit": "tin"}]),
    138: ("श्री विक्रम जी जाट (उपाध्यक्ष, लोधा समाज इंदौर) - भंडारे में संपूर्ण चावल",
          None, [{"type": "rice", "note": "भंडारे में संपूर्ण चावल"}]),
    # Source has a stray "8-" at the start and no separator.
    # REVIEW: the समाज should fix this line in the source.
    154: ("8- स्वर्गीय वरुण वेंकट जी उनके परिवार कि और से ₹5'555/-",
          "स्वर्गीय वरुण वेंकट जी उनके परिवार कि ओर से",
          [{"type": "cash", "qty": 5555, "unit": "inr"}]),
}

# Hand-reviewed: the donor themself is the person who has died, so the list
# carries their name in memoriam. Carried over from the earlier review of the
# same two people; every other death-marked entry names someone else and is
# printed under "awaiting review" instead.
MEMORIAM = {45: "श्रीमती आशा जी जाट", 78: "श्री अमर जी भवानी"}


def clean_name(raw: str) -> str:
    """Light, explicit tidying only — never a rewording."""
    text = unicodedata.normalize("NFC", raw).strip().rstrip(",")
    text = text.replace("स्व•", "स्व. ").replace("स्व.", "स्व. ")
    text = re.sub(r"\s*-\s*", " ", text)        # "A-B" names into "A B"
    text = re.sub(r"\s*\(([^)]*?)\s*वाले\)", r" (\1)", text)   # "(बाल्दा वाले)" -> "(बाल्दा)"
    return re.sub(r"\s+", " ", text).strip()


def parse_items(segment_text: str, number: int) -> list[dict]:
    items = []
    for seg in (s.strip() for s in segment_text.split("+")):
        if "*" in seg:
            raise ValueError(f"#{number}: {seg!r} carries an unexplained '*'")
        money = MONEY.match(seg)
        if money:
            items.append({"type": "cash", "qty": int(money.group(1).replace("'", "")),
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
            if word in TYPE_WORDS and code is None:
                code = TYPE_WORDS[word]
            elif word in UNIT_WORDS and unit is None:
                unit = UNIT_WORDS[word]
            elif word not in FILLER:
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


def read_source() -> list[tuple[int, str]]:
    rows = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        m = ENTRY.match(line.strip())
        if m:
            rows.append((int(m.group(1)), unicodedata.normalize("NFC", m.group(2).strip())))
    return rows


def build(rows) -> tuple[list[dict], list[str]]:
    donors, notes = [], []
    seen_numbers = [n for n, _ in rows]
    expected = list(range(1, len(rows) + 1))
    if seen_numbers != expected:
        raise ValueError(f"entries are not numbered 1..{len(rows)} without gaps: "
                         f"{sorted(set(expected) ^ set(seen_numbers))}")

    for number, text in rows:
        override = OVERRIDES.get(number)
        if override:
            ruled_against, name_override, items = override
            if text != unicodedata.normalize("NFC", ruled_against):
                raise ValueError(
                    f"#{number} has an OVERRIDES entry written against\n"
                    f"    {ruled_against!r}\n  but the source now reads\n"
                    f"    {text!r}\n  Re-review that ruling before importing.")
            name = clean_name(name_override if name_override else
                              SEP.sub("\x00", text).rsplit("\x00", 1)[0])
            items = [dict(i) for i in items]
        else:
            if not SEP.search(text):
                raise ValueError(f"#{number}: {text!r} has no ' - ' between the "
                                 f"name and the contribution")
            raw_name, raw_items = SEP.sub("\x00", text).rsplit("\x00", 1)
            name = clean_name(raw_name)
            items = parse_items(raw_items, number)

        donor = {"name": {"hi": name}}
        if number in MEMORIAM:
            if not DEATH_MARKER.match(name):
                raise ValueError(
                    f"#{number} is in MEMORIAM but its name {name!r} carries no "
                    f"death marker — the source has shifted; re-review MEMORIAM")
            expected_name = MEMORIAM[number]
            donor["name"]["hi"] = expected_name
            donor["memoriam"] = True
            if expected_name not in clean_name(DEATH_MARKER.sub("", name)):
                raise ValueError(
                    f"#{number} in MEMORIAM should be {expected_name!r} but the "
                    f"source names {name!r} — re-review MEMORIAM")
        elif DEATH_MARKER.match(name):
            notes.append(f"  #{number}: {name}")
        donor["items"] = items
        donors.append(donor)
    return donors, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="parse and report, write nothing")
    args = ap.parse_args()

    later = sorted(p.name for p in OUT.parent.glob("donors-[0-9][0-9][0-9][0-9].json")
                   if p != OUT)
    if later:
        print(f"REFUSED: {', '.join(later)} also exist. This script only rewrites "
              f"{OUT.name}; check donors-index.json by hand afterwards.")

    rows = read_source()
    try:
        donors, awaiting = build(rows)
    except ValueError as exc:
        print(f"FAILED: {exc}")
        return 1

    print(f"{len(rows)} entries in the source -> {len(donors)} donors")
    print(f"in memoriam (hand-reviewed): {sum(1 for d in donors if d.get('memoriam'))}")
    if awaiting:
        print(f"\ndeath-marked names NOT flagged, awaiting the समाज's review "
              f"({len(awaiting)}). In this list the marker usually names an "
              f"ancestor, not the donor:")
        print("\n".join(awaiting))

    if args.check:
        print("\n--check: nothing written")
        return 0
    payload = {"year": YEAR, "festival": FESTIVAL, "donors": donors}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
