#!/usr/bin/env python3
"""Give every donor a Donor ID that links their gifts across all lists.

Run after any converter, before validating and pushing:

    python3 tools/convert_<list>.py
    python3 tools/assign_donor_ids.py [--check]
    python3 tools/validate_donors.py

Reads every list named in data/donors-index.json ("years" and "lists") and the
register data/donors.json; writes "donorIds" into each list entry, adds new
donors and spellings to the register, and rewrites the private review file
docs/donor-review.json.

Only near-certain matches are linked: the same name once honorifics and
bracketed places are set aside, with places that agree and the same स्वर्गीय
status. Everything doubtful becomes a review item for the समाज to answer with
"same": true / false. This script never guesses, never deletes an ID, and gives
the same output for the same input.
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from convert_2025_md import DEATH_MARKER

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REVIEW = ROOT / "docs" / "donor-review.json"

HONORIFICS = {"श्री", "श्रीमती", "जी", "स्व.", "स्वर्गीय", "स्वर्ग", "पंडित"}
# A श्री after one of these belongs to the same donor ("… बाई के पुत्र श्री गोलू").
CONNECTORS = {"के", "की", "का", "पुत्र", "पुत्री", "पत्नी"}
FAMILY_WORDS = {"का", "की", "के", "परिवार", "द्वारा", "ओर", "से"}
# Spelling variants seen across the lists; used only to SUGGEST a review pair.
WORD_FOLDS = {"जामदार": "जमदार", "वेंकट": "बंकट"}
CHAR_FOLDS = str.maketrans({"ौ": "ो", "ू": "ु", "ी": "ि", "झ": "ज"})
BRACKET = re.compile(r"\(([^)]*)\)")
JOINERS = re.compile(r"\s+एवं\s+|\s+और\s+|\s*,\s*")
ANONYMOUS = re.compile(r"^गुप्त\s+दान")


def _words(text: str) -> list[str]:
    """Words of a name with bracketed text and honorifics set aside."""
    return [w for w in BRACKET.sub(" ", text).split() if w not in HONORIFICS]


def strict_key(text: str) -> str:
    return " ".join(_words(unicodedata.normalize("NFC", text)))


def loose_key(text: str) -> str:
    words = [w for w in _words(unicodedata.normalize("NFC", text)) if w not in FAMILY_WORDS]
    return " ".join(WORD_FOLDS.get(w, w).translate(CHAR_FOLDS) for w in words)


def place_of(text: str) -> str:
    return " ".join(" ".join(m.split()) for m in BRACKET.findall(text))


def places_compatible(a: str, b: str) -> bool:
    return not a or not b or a in b or b in a


def is_memorial(text: str) -> bool:
    return bool(DEATH_MARKER.match(text))


def split_people(name: str) -> list[dict]:
    """[{"text", "memorial"}] for each person in a printed name who gets an ID.

    Splits on एवं / और / commas (never inside brackets) and before a second
    श्री/श्रीमती. A memorial in a joint entry is dropped; when every person is a
    memorial they all stay. "गुप्त दान" is anonymous and names nobody.
    """
    name = unicodedata.normalize("NFC", name).strip()
    if ANONYMOUS.match(name):
        return []
    held: list[str] = []

    def hold(m):
        held.append(m.group(0))
        return f"\x00{len(held) - 1}\x00"

    def restore(s):
        return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], s).strip()

    segments = []
    for part in JOINERS.split(BRACKET.sub(hold, name)):
        current: list[str] = []
        for tok in part.split():
            if (tok in ("श्री", "श्रीमती") and current
                    and current[-1] not in HONORIFICS and current[-1] not in CONNECTORS):
                segments.append(" ".join(current))
                current = []
            current.append(tok)
        if current:
            segments.append(" ".join(current))

    people: list[dict] = []
    for seg in segments:
        text = restore(seg)
        if people and not loose_key(text):        # "… एवं परिवार"
            people[-1]["text"] += " एवं " + text
            continue
        people.append({"text": text, "memorial": is_memorial(text)})
    living = [p for p in people if not p["memorial"]]
    return living or people


def new_register() -> dict:
    return {"donors": {}, "merged": {}, "distinct": [], "sameInList": [], "pins": {}}


def resolve(register: dict, did: str) -> str | None:
    """The kept ID for `did` (following a merge), or None if it is not a donor."""
    did = register["merged"].get(did, did)
    return did if did in register["donors"] else None


def _next_id(register: dict) -> str:
    used = [int(i[1:]) for i in [*register["donors"], *register["merged"]]]
    return f"D{max(used, default=0) + 1:04d}"


class _Lookup:
    """Alias and key indexes over the register, kept current as donors are added."""

    def __init__(self, register: dict):
        self.register = register
        self.by_alias: dict[str, str] = {}
        self.by_key: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for did, donor in register["donors"].items():
            for alias in donor["aliases"]:
                self._add(did, alias)

    def _add(self, did: str, alias: str) -> None:
        self.by_alias[alias] = did
        self.by_key[strict_key(alias)].append((did, alias))

    def find_or_create(self, person: dict) -> str:
        text = person["text"]
        if text in self.by_alias:
            return self.by_alias[text]
        place = place_of(text)
        compatible = sorted({did for did, alias in self.by_key.get(strict_key(text), [])
                             if places_compatible(place, place_of(alias))
                             and is_memorial(alias) == person["memorial"]})
        if len(compatible) == 1:
            did = compatible[0]
        else:
            did = _next_id(self.register)
            self.register["donors"][did] = {"name": {"hi": text}, "aliases": []}
        self.register["donors"][did]["aliases"].append(text)
        self._add(did, text)
        return did


def _set_ids(entry: dict, ids: list[str]) -> None:
    name = entry["name"]
    rest = {k: v for k, v in entry.items() if k not in ("name", "donorIds")}
    entry.clear()
    entry.update({"name": name, "donorIds": ids, **rest})


def assign(register: dict, lists: list[tuple[str, dict]]) -> dict[str, str]:
    """Write donorIds into every entry; return {id: last spelling seen}."""
    lookup = _Lookup(register)
    last_seen: dict[str, str] = {}
    for key, data in lists:
        for pos, item in enumerate(data["donors"], 1):
            ref = f"{key}#{pos}"
            printed = item["name"]["hi"]
            pin = register["pins"].get(ref)
            if pin:
                if pin["name"] != printed:
                    raise ValueError(
                        f"{ref} is pinned to {pin['name']!r} but the list now reads "
                        f"{printed!r}. The list has changed: re-review that pin in "
                        f"data/donors.json before running again.")
                ids = list(pin["donorIds"])
            else:
                ids = []
                for person in split_people(printed):
                    did = lookup.find_or_create(person)
                    if did not in ids:
                        ids.append(did)
                    last_seen[did] = person["text"]
            _set_ids(item, ids)
    return last_seen


def rename(register: dict, last_seen: dict[str, str]) -> None:
    for did, text in last_seen.items():
        donor = register["donors"].get(did)
        if donor and not donor.get("fixedName"):
            donor["name"]["hi"] = text
