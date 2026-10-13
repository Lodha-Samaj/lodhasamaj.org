#!/usr/bin/env python3
"""Convert the 2025 donor HTML page into data/donors-2025.json.

SPENT ONE-OFF. This ran once to import the old 2025 page. Its SOURCE path
exists only on the original machine, and it ends by overwriting
data/donors-index.json with {"years": [2025]}, which would silently delete any
later year from the archive. It therefore refuses to run once any other
data/donors-YYYY.json exists. Edit data/donors-2025.json by hand from now on.

Re-runnable: the source page is still being edited by the समाज, so this
parses the page's own दान/प्रकार fields rather than carrying a hand table.
Two descriptive rows and the memoriam set are the only hand-held parts.
"""
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

SOURCE = Path("/d-data/Data/Lodha-Samaj-2025/"
              "Lodha-Samaj-Navratri-Utsav-Daanata-Suchi-2025.html")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "donors-2025.json"
INDEX = ROOT / "data" / "donors-index.json"

# प्रकार label on the page -> type code. Longest first where one is a
# prefix of another, because the lookup is first-match.
TYPE_WORDS = [
    ("केले के पत्तल", "pattal"), ("गैस टंकी", "gas"), ("शुद्ध घी", "ghee"),
    ("शक्कर", "sugar"), ("आटा", "flour"), ("तेल", "oil"), ("नमक", "salt"),
    ("मावा", "mawa"), ("नगद", "cash"), ("पानी", "water"), ("नारियल", "coconut"),
    ("बेसन", "besan"), ("गैस", "gas"), ("घी", "ghee"),
]
UNIT_WORDS = {"किलो": "kg", "डब्बा": "tin", "जार": "jar", "छोटी": "cylinder"}

# Rows whose दान field is descriptive rather than numeric. Index -> items.
OVERRIDES = {
    24: [{"type": "pattal", "note": "सम्पूर्ण भंडारे हेतु"}],
    74: [{"type": "coconut", "note": "कन्या पूजन हेतु संपूर्ण श्रीफल"}],
}

# Hand-reviewed: the donor themself is deceased. See the table in the plan.
MEMORIAM = {49, 75}

DEATH_MARKER = re.compile(r"^\s*(?:स्व\s*[.•]|स्वर्गीय)\s*")


def clean(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)          # strips <br>, </br>, <span>
    text = re.sub(r"\s+", " ", text).strip()
    return unicodedata.normalize("NFC", text)


def type_from_text(text: str):
    for word, code in TYPE_WORDS:
        if word in text:
            return code
    return None


def prakar_parts(prakar: str) -> list[str]:
    """Split the प्रकार field into words, dropping parenthesised notes."""
    parts = []
    for part in prakar.split(","):
        part = re.sub(r"\(.*?\)", "", part).strip()
        if part:
            parts.append(part)
    return parts


def unknown_prakar_words(prakar: str) -> list[str]:
    """Words in the प्रकार field that no TYPE_WORDS entry recognises."""
    return [part for part in prakar_parts(prakar) if type_from_text(part) is None]


def types_from_prakar(prakar: str) -> list[str]:
    """The प्रकार field, e.g. 'शक्कर, आटा' or 'नारियल (कन्या पूजन हेतु)'."""
    codes = []
    for part in prakar_parts(prakar):
        code = type_from_text(part)
        if code is None:
            raise ValueError(f"unrecognised प्रकार word {part!r} in {prakar!r}")
        codes.append(code)
    return codes


def to_int(text: str) -> int:
    return int(text.replace(",", "").replace("₹", "").strip())


def positional_type(position: int, fallback: list, segment: str,
                    index: int, prakar: str) -> str:
    """Type for a segment with no type word of its own, taken from प्रकार.

    Fails rather than guessing: an empty प्रकार, a position the प्रकार field
    does not cover when it names several types, or a missing type all raise.
    The single-type case (donor #27) is unambiguous and is allowed.
    """
    if not fallback:
        raise ValueError(
            f"donor #{index}: segment {segment!r} has no type word and "
            f"प्रकार={prakar!r} names no type. Add an entry to OVERRIDES.")
    if position < len(fallback):
        code = fallback[position]
    elif len(fallback) == 1:
        code = fallback[0]
    else:
        raise ValueError(
            f"donor #{index}: segment {segment!r} needs the प्रकार fallback "
            f"but has no type word, and प्रकार={prakar!r} lists "
            f"{len(fallback)} types for position {position + 1}. "
            f"Add an entry to OVERRIDES.")
    if code is None:
        raise ValueError(
            f"donor #{index}: no type for segment {segment!r} from "
            f"प्रकार={prakar!r}. Add an entry to OVERRIDES.")
    return code


def parse_items(dan: str, prakar: str, index: int) -> list[dict]:
    """Parse one donor's दान field into structured items."""
    if index in OVERRIDES:
        return [dict(item) for item in OVERRIDES[index]]

    fallback = types_from_prakar(prakar)
    items: list[dict] = []
    for position, segment in enumerate([s.strip() for s in dan.split("+")]):
        def pick_type(text):
            own = type_from_text(text)
            if own is not None:
                return own
            return positional_type(position, fallback, segment, index, prakar)

        match = re.fullmatch(r"₹\s*([\d,]+)", segment)
        if match:
            items.append({"type": "cash", "qty": to_int(match.group(1)), "unit": "inr"})
            continue

        match = re.fullmatch(r"([\d,]+)\s*पानी\s*जार", segment)
        if match:
            items.append({"type": "water", "qty": to_int(match.group(1)), "unit": "jar"})
            continue

        match = re.fullmatch(r"([\d,]+)\s*छोटी\s*गैस\s*टंकी", segment)
        if match:
            items.append({"type": "gas", "qty": to_int(match.group(1)), "unit": "cylinder"})
            continue

        match = re.fullmatch(r"([\d,]+)\s*(किलो|डब्बा|जार|छोटी)\s*(.*)", segment)
        if match:
            qty, unit_word, rest = match.groups()
            item = {"type": pick_type(rest), "qty": to_int(qty),
                    "unit": UNIT_WORDS[unit_word]}
            if rest and type_from_text(rest) is None:
                item["note"] = rest.strip()
            items.append(item)
            continue

        match = re.fullmatch(r"([\d,]+)", segment)       # bare number, e.g. '51' coconuts
        if match:
            item_type = positional_type(position, fallback, segment, index, prakar)
            items.append({"type": item_type, "qty": to_int(match.group(1)),
                          "unit": "piece"})
            continue

        raise ValueError(
            f"donor #{index}: cannot parse दान segment {segment!r} "
            f"(प्रकार={prakar!r}). Add an entry to OVERRIDES."
        )
    return items


# SUPERSEDED by tools/convert_2025_md.py, which imports the समाज's own markdown
# सहयोगकर्ता सूची. That list has 166 entries; the website HTML this script reads
# has 82 of them. Running this again would silently drop 84 donors, so it now
# refuses. Kept for its parsing history and its tests.
SUPERSEDED_BY = "tools/convert_2025_md.py"


def main() -> int:
    print(f"REFUSED: this import is superseded by {SUPERSEDED_BY}, which reads the "
          f"समाज's full markdown list (166 entries against this page's 82). "
          f"Running this would drop 84 donors from data/donors-2025.json.")
    return 1


def main_unused() -> int:
    later = sorted(p.name for p in OUT.parent.glob("donors-[0-9][0-9][0-9][0-9].json")
                   if p != OUT)
    if later:
        print(f"REFUSED: {', '.join(later)} exists. This script rewrites "
              "donors-index.json to list only 2025 and would drop those years. "
              "It was a one-off import; edit the JSON by hand instead.")
        return 1
    html = SOURCE.read_text(encoding="utf-8")
    cards = re.split(r'<div class="donor-card">', html)[1:]
    if not cards:
        print("no donor cards found — has the page markup changed?")
        return 1

    donors = []
    for index, card in enumerate(cards, start=1):
        name = clean(re.search(r"<h3>(.*?)</h3>", card, re.S).group(1))
        dan = clean(re.search(r"<strong>दान:</strong>(.*?)</p>", card, re.S).group(1))
        prakar = clean(re.search(r"<strong>प्रकार:</strong>(.*?)</p>", card, re.S).group(1))

        # Shift guards: MEMORIAM and OVERRIDES are keyed on card position, so
        # check each index still points at the row it was reviewed for.
        if index in MEMORIAM and not DEATH_MARKER.match(name):
            print(f"donor #{index} is in MEMORIAM but its name {name!r} carries "
                  f"no स्व./स्व•/स्वर्गीय marker — the page has shifted; "
                  f"re-review the MEMORIAM set")
            return 1
        if index in OVERRIDES and re.match(r"\s*[\d₹]", dan):
            print(f"donor #{index} has an OVERRIDES entry but its दान {dan!r} is "
                  f"a parseable quantity — the page has shifted; re-review OVERRIDES")
            return 1
        unknown = unknown_prakar_words(prakar)
        if unknown:
            print(f"donor #{index} ({name}): प्रकार {prakar!r} contains unrecognised "
                  f"type word {unknown[0]!r} — add it to TYPE_WORDS and to the type "
                  f"vocabulary before re-running")
            return 1

        donor = {"name": {"hi": name}}
        if index in MEMORIAM:
            donor["name"]["hi"] = DEATH_MARKER.sub("", name)
            donor["memoriam"] = True
        try:
            donor["items"] = parse_items(dan, prakar, index)
        except ValueError as exc:
            print(exc)
            return 1
        if any(item.get("type") is None for item in donor["items"]):
            print(f"donor #{index} ({name}): could not resolve a type from "
                  f"दान={dan!r} प्रकार={prakar!r}")
            return 1
        donors.append(donor)

    payload = {
        "year": 2025,
        "festival": {"bhandara": 45, "kanyaPujan": 22},
        "donors": donors,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    INDEX.write_text(json.dumps({"years": [2025]}, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")

    totals = collections.Counter()
    for donor in donors:
        for item in donor["items"]:
            if isinstance(item.get("qty"), (int, float)) and item.get("unit"):
                totals[(item["type"], item["unit"])] += item["qty"]
    print(f"wrote {OUT} with {len(donors)} donors")
    for key in sorted(totals):
        print(f"  {key[0]:<8} {key[1]:<9} {totals[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
