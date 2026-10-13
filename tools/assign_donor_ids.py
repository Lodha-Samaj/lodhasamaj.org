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
"same": true / false. A question the rules cannot find is posed by adding the
pair to "ask" in data/donors.json, e.g. "ask": [["D0012", "D0034"]]; it stays
in the review file until answered. This script never guesses, never deletes an
ID, and gives the same output for the same input.
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
LOOSE_JOINERS = {"एवं", "और"}
# Titles that may be printed or left out; set aside to SUGGEST a pair, never to link.
LOOSE_TITLES = {"आचार्य", "डॉ."}
PLACE_PUNCT = re.compile(r"[,:;.]")
BRACKET = re.compile(r"\(([^)]*)\)")
JOINERS = re.compile(r"(\s+एवं\s+|\s+और\s+|\s*,\s*)")   # captured: kept as printed
ANONYMOUS = re.compile(r"^गुप्त\s+दान")


def _words(text: str) -> list[str]:
    """Words of a name with bracketed text and honorifics set aside."""
    return [w for w in BRACKET.sub(" ", text).split() if w not in HONORIFICS]


def strict_key(text: str) -> str:
    return " ".join(_words(unicodedata.normalize("NFC", text)))


def _bare_words(text: str) -> list[str]:
    """Words without honorifics, brackets, family wording or joiners (never used to auto-link)."""
    return [w for w in _words(unicodedata.normalize("NFC", text))
            if w not in FAMILY_WORDS and w not in LOOSE_JOINERS]


def loose_key(text: str) -> str:
    return " ".join(WORD_FOLDS.get(w, w).translate(CHAR_FOLDS)
                    for w in _bare_words(text) if w not in LOOSE_TITLES)


def place_of(text: str) -> str:
    return " ".join(" ".join(m.split()) for m in BRACKET.findall(text))


def _place_words(place: str) -> list[str]:
    return PLACE_PUNCT.sub(" ", place).split()


def _within(short: list[str], long: list[str]) -> bool:
    """Every word of `short`, in order, among the words of `long`."""
    rest = iter(long)
    return all(w in rest for w in short)


def places_compatible(a: str, b: str) -> bool:
    """Places agree when either is absent or one's words lie, in order, within the other's."""
    x, y = _place_words(a), _place_words(b)
    return not x or not y or _within(x, y) or _within(y, x)


def is_memorial(text: str) -> bool:
    return bool(DEATH_MARKER.match(text))


def _plain(tok: str) -> bool:
    """A name word: not an honorific, connector, family word, joiner or held bracket."""
    return not (tok in HONORIFICS or tok in CONNECTORS or tok in FAMILY_WORDS
                or tok in LOOSE_JOINERS or tok.startswith("\x00"))


def _second_person_starts(current: list[str], toks: list[str], i: int) -> bool:
    """A second person begins at toks[i] without a श्री of their own.

    "श्री कलवा जी जमदार आशीष जी जमदार": after "<given> जी <surname>" comes a
    plain word and another जी follows; or the surname just finished is printed
    again later ("स्वर्गीय आदित्य जी जमदार रंजीत जमदार").
    """
    if len(current) < 2 or not _plain(toks[i]) or not _plain(current[-1]):
        return False
    if not any(_plain(w) for w in current[:-1]):    # a given name before the surname
        return False
    surname = current[-1]
    return ((current[-2] == "जी" and "जी" in toks[i + 1:])
            or surname in toks[i + 1:])


def split_people(name: str) -> list[dict]:
    """[{"text", "memorial"}] for each person in a printed name who gets an ID.

    Splits on एवं / और / commas (never inside brackets), before a second
    श्री/श्रीमती, and where a second person starts without one (see
    _second_person_starts). A memorial in a joint entry is dropped; when every person is a
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

    pieces = JOINERS.split(BRACKET.sub(hold, name))
    segments: list[tuple[str, str]] = []           # (separator printed before it, text)
    for n in range(0, len(pieces), 2):
        sep = pieces[n - 1] if n else ""
        current: list[str] = []
        toks = pieces[n].split()
        for i, tok in enumerate(toks):
            if ((tok in ("श्री", "श्रीमती") and current
                    and current[-1] not in HONORIFICS and current[-1] not in CONNECTORS)
                    or _second_person_starts(current, toks, i)):
                segments.append((sep, " ".join(current)))
                current, sep = [], " "
            current.append(tok)
        if current:
            segments.append((sep, " ".join(current)))

    people: list[dict] = []
    for sep, seg in segments:
        text = restore(seg)
        if people and not loose_key(text):        # "… एवं परिवार", "… की और से"
            people[-1]["text"] += sep + text
            continue
        people.append({"text": text, "memorial": is_memorial(text)})
    living = [p for p in people if not p["memorial"]]
    return living or people


def new_register() -> dict:
    return {"donors": {}, "merged": {}, "distinct": [], "sameInList": [], "pins": {}, "ask": []}


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
        # A donor is a match only if EVERY one of its spellings with this key
        # agrees on place and स्वर्गीय status: one place-less alias must not make
        # "(दिल्ली)" and "(महू)" the same person.
        same_key: dict[str, list[str]] = defaultdict(list)
        for did, alias in self.by_key.get(strict_key(text), []):
            same_key[did].append(alias)
        compatible = sorted(did for did, aliases in same_key.items()
                            if all(places_compatible(place, place_of(alias))
                                   and is_memorial(alias) == person["memorial"]
                                   for alias in aliases))
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


def _why(kind: str, x: str, y: str) -> str:
    if kind == "loose":
        if _bare_words(x) == _bare_words(y):
            return f"family wording: {strict_key(x)} / {strict_key(y)}"
        return f"spelling: {strict_key(x)} / {strict_key(y)}"
    if is_memorial(x) != is_memorial(y):
        return "one name is स्वर्गीय"
    if not places_compatible(place_of(x), place_of(y)):
        return "same name, different place"
    return "same name, kept apart"


_RANK = {"one name is स्वर्गीय": 0, "same name, different place": 1}


def review_items(register: dict, lists: list[tuple[str, dict]]) -> list[dict]:
    donors = register["donors"]
    distinct = {tuple(p) for p in register["distinct"]}
    where: dict[str, list[str]] = defaultdict(list)
    for key, data in lists:
        for item in data["donors"]:
            for did in item.get("donorIds", []):
                if key not in where[did]:
                    where[did].append(key)

    def side(did):
        return {"id": did, "name": donors[did]["name"]["hi"], "lists": where.get(did, [])}

    by_strict: dict[str, list] = defaultdict(list)
    by_loose: dict[str, list] = defaultdict(list)
    for did, donor in donors.items():
        for alias in donor["aliases"]:
            by_strict[strict_key(alias)].append((did, alias))
            by_loose[loose_key(alias)].append((did, alias))
    found: dict[tuple[str, str], str] = {}
    for kind, index in (("strict", by_strict), ("loose", by_loose)):
        reasons: dict[tuple[str, str], list[str]] = defaultdict(list)
        for members in index.values():
            for (x_id, x), (y_id, y) in combinations(sorted(members), 2):
                pair = (x_id, y_id)
                if x_id == y_id or pair in distinct or pair in found:
                    continue
                reasons[pair].append(_why(kind, x, y))
        for pair, whys in reasons.items():
            # Judge the pair of donors, not one pair of spellings: the strongest
            # reason any two of their spellings give.
            found[pair] = min(whys, key=lambda w: (_RANK.get(w, len(_RANK)), whys.index(w)))
    # "श्री कालू जमदार" / "श्री कालू हजारीलाल जी जमदार": the same given name and
    # surname with a word (often the father's name) added. Asked, never linked.
    by_ends: dict[tuple[str, str], list] = defaultdict(list)
    for did, donor in donors.items():
        for alias in donor["aliases"]:
            words = [WORD_FOLDS.get(w, w).translate(CHAR_FOLDS) for w in strict_key(alias).split()]
            if words:
                by_ends[(words[0], words[-1])].append((did, alias, set(words)))
    for members in by_ends.values():
        for (x_id, x, xw), (y_id, y, yw) in combinations(sorted(members, key=lambda m: m[:2]), 2):
            pair = (x_id, y_id)
            if x_id == y_id or pair in distinct or pair in found:
                continue
            if xw < yw or yw < xw:
                found[pair] = f"name with an extra word: {strict_key(x)} / {strict_key(y)}"

    # Questions the rules cannot find, written into "ask" by hand.
    for pair in register.get("ask", []):
        x, y = sorted(resolve(register, d) or "" for d in pair)
        if x and y and x != y and (x, y) not in distinct:
            found[(x, y)] = "asked by the samaj"

    items = [{"kind": "pair", "a": side(x), "b": side(y), "reason": why, "same": None}
             for (x, y), why in sorted(found.items())]

    same_in_list = set(register["sameInList"])
    for key, data in lists:
        positions: dict[str, list[int]] = defaultdict(list)
        for pos, item in enumerate(data["donors"], 1):
            for did in item.get("donorIds", []):
                positions[did].append(pos)
        for did, where_in in sorted(positions.items()):
            if len(where_in) > 1 and f"{key}:{did}" not in same_in_list:
                items.append({
                    "kind": "repeat", "id": did, "name": donors[did]["name"]["hi"], "list": key,
                    "entries": [{"ref": f"{key}#{p}", "name": data["donors"][p - 1]["name"]["hi"]}
                                for p in where_in],
                    "reason": "same name twice in one list", "same": None})
    return items


def merge(register: dict, a_id: str, b_id: str) -> None:
    keep, gone = sorted([a_id, b_id])
    donors = register["donors"]
    for alias in donors[gone]["aliases"]:
        if alias not in donors[keep]["aliases"]:
            donors[keep]["aliases"].append(alias)
    kept, removed = donors[keep], donors[gone]
    if removed.get("fixedName") and not kept.get("fixedName"):
        kept["name"] = {**kept["name"], **removed["name"]}   # the hand-set name wins
        kept["fixedName"] = True
    elif "en" in removed["name"] and "en" not in kept["name"]:
        kept["name"]["en"] = removed["name"]["en"]
    del donors[gone]
    register["merged"][gone] = keep
    for old, target in list(register["merged"].items()):
        if target == gone:
            register["merged"][old] = keep
    for name in ("distinct", "ask"):
        pairs = {tuple(sorted(keep if d == gone else d for d in p)) for p in register[name]}
        register[name] = [list(p) for p in sorted(pairs) if p[0] != p[1]]
    for pin in register["pins"].values():
        pin["donorIds"] = list(dict.fromkeys(keep if d == gone else d for d in pin["donorIds"]))
    register["sameInList"] = sorted({s[: -len(gone)] + keep if s.endswith(":" + gone) else s
                                     for s in register["sameInList"]})


def _label(item: dict) -> str:
    if item.get("kind") == "repeat":
        return f"{item.get('id')} in {item.get('list')}"
    return f"{item.get('a', {}).get('id')} / {item.get('b', {}).get('id')}"


def apply_answers(register: dict, items: list, lists: list[tuple[str, dict]]) -> int:
    by_key = dict(lists)
    applied = 0
    for n, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"docs/donor-review.json item #{n} is not an object")
        same = item.get("same")
        if not (same is None or same is True or same is False):
            raise ValueError(f"docs/donor-review.json item #{n} ({_label(item)}): "
                             f"\"same\" is {same!r} - write true, false or null")
        if same is None:
            continue
        applied += 1
        try:
            if item["kind"] == "repeat":
                old = resolve(register, item["id"])
                tag = f"{item['list']}:{old}"
                if same:
                    if tag not in register["sameInList"]:
                        register["sameInList"].append(tag)
                    continue
                for ent in item["entries"][1:]:
                    key, pos = ent["ref"].rsplit("#", 1)
                    target = by_key[key]["donors"][int(pos) - 1]
                    if target["name"]["hi"] != ent["name"]:
                        raise ValueError(
                            f"{ent['ref']} now reads {target['name']['hi']!r}, not "
                            f"{ent['name']!r}: the list changed after the review file was "
                            f"written. Set this item back to null and run again.")
                    new = _next_id(register)
                    register["donors"][new] = {"name": dict(register["donors"][old]["name"]),
                                               "aliases": []}
                    register["pins"][ent["ref"]] = {
                        "name": ent["name"],
                        "donorIds": [new if resolve(register, d) == old else d
                                     for d in target["donorIds"]]}
            else:
                x, y = resolve(register, item["a"]["id"]), resolve(register, item["b"]["id"])
                if x is None or y is None or x == y:
                    continue
                register["ask"] = [p for p in register["ask"]
                                   if sorted(resolve(register, d) or d for d in p) != sorted([x, y])]
                if same:
                    merge(register, x, y)
                elif sorted([x, y]) not in register["distinct"]:
                    register["distinct"].append(sorted([x, y]))
        except KeyError as exc:
            raise ValueError(f"docs/donor-review.json item #{n} is missing {exc}") from None
    register["distinct"].sort()
    register["sameInList"].sort()
    return applied


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def load_lists(data_dir: Path) -> list[tuple[str, Path, dict]]:
    """Every list in processing order: years ascending, then named lists."""
    index = json.loads((data_dir / "donors-index.json").read_text(encoding="utf-8"))
    order = [(str(y), data_dir / f"donors-{y}.json") for y in sorted(index.get("years", []))]
    order += [(slug, data_dir / f"{slug}.json") for slug in index.get("lists", [])]
    return [(key, path, json.loads(path.read_text(encoding="utf-8"))) for key, path in order]


def run(data_dir: Path, review_path: Path, write: bool = True) -> dict:
    register_path = data_dir / "donors.json"
    register = new_register()
    if register_path.exists():
        register.update(json.loads(register_path.read_text(encoding="utf-8")))
    ask = register["ask"]
    if not (isinstance(ask, list) and all(
            isinstance(p, list) and len(p) == 2 and all(isinstance(d, str) for d in p) for p in ask)):
        raise ValueError('data/donors.json: "ask" must be a list of ID pairs, like '
                         '[["D0012", "D0034"]]')
    loaded = load_lists(data_dir)
    lists = [(key, data) for key, _, data in loaded]

    assign(register, lists)                  # pass 1: IDs the answers can refer to
    answers = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else []
    if not isinstance(answers, list):
        raise ValueError("docs/donor-review.json must be a list: [ {...}, {...} ]")
    applied = apply_answers(register, answers, lists)
    rename(register, assign(register, lists))   # pass 2: merges and pins applied
    items = review_items(register, lists)

    if write:
        ordered = {"donors": dict(sorted(register["donors"].items())),
                   "merged": dict(sorted(register["merged"].items())),
                   "distinct": register["distinct"],
                   "sameInList": register["sameInList"],
                   "pins": dict(sorted(register["pins"].items())),
                   "ask": register["ask"]}
        register_path.write_text(_dump(ordered), encoding="utf-8")
        for _, path, data in loaded:
            path.write_text(_dump(data), encoding="utf-8")
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(_dump(items), encoding="utf-8")
    return {"entries": sum(len(d["donors"]) for _, d in lists),
            "donors": len(register["donors"]), "applied": applied, "review": len(items)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report, write nothing")
    args = ap.parse_args(argv[1:])
    try:
        summary = run(DATA, REVIEW, write=not args.check)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"FAILED: {exc}")
        return 1
    print(f"{summary['entries']} list entries -> {summary['donors']} donors")
    print(f"answers applied from the review file: {summary['applied']}")
    print(f"review items awaiting the समाज: {summary['review']} "
          f"(docs/donor-review.json - set \"same\" to true or false, then run again)")
    if args.check:
        print("--check: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
