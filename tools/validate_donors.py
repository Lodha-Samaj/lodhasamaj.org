#!/usr/bin/env python3
"""Validate data/donors-*.json, and any named list a page shows through
data-list (data/<slug>.json), against the field rules in the design spec.

Usage: python3 tools/validate_donors.py [path ...]
Exits 1 if any file has errors. No third-party dependencies.
"""
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

TYPES = {"sugar", "flour", "oil", "salt", "ghee", "mawa", "cash",
         "water", "gas", "coconut", "pattal", "besan", "rava", "rice",
         "cement", "brick", "rebar", "tiles", "fan", "other"}
UNITS = {"kg", "tin", "inr", "jar", "cylinder", "piece", "bag", "count"}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DONOR_ID = re.compile(r"^D\d{4}$")


def _is_number(value) -> bool:
    # bool is a subclass of int in Python, so exclude it explicitly.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (isinstance(value, float) and not math.isfinite(value))


def validate_file(path: str) -> list[str]:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{p.name}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{p.name}: cannot read the file ({exc.__class__.__name__}: {exc})"]

    if not isinstance(data, dict):
        return [f"{p.name}: top level must be an object, got {type(data).__name__}"]

    errors: list[str] = []
    year = data.get("year")
    match = re.search(r"donors-(\d{4})\.json$", p.name)
    if not match and "list" in data:
        # A named list (a campaign, not a year): it names itself and its title.
        if data["list"] != p.stem:
            errors.append(f"{p.name}: 'list' is {data['list']!r} but the filename says {p.stem}")
        title = data.get("title")
        if not isinstance(title, dict) or not isinstance(title.get("hi"), str) or not title["hi"].strip():
            errors.append(f"{p.name}: a named list needs a title.hi for its page heading")
    elif isinstance(year, bool) or not isinstance(year, int):
        errors.append(f"{p.name}: 'year' must be an integer")
    elif match and int(match.group(1)) != year:
        errors.append(f"{p.name}: 'year' is {year} but the filename says {match.group(1)}")

    donors = data.get("donors")
    if not isinstance(donors, list):
        return errors + [f"{p.name}: 'donors' must be a list"]

    for i, donor in enumerate(donors):
        if not isinstance(donor, dict):
            errors.append(f"{p.name}: donor #{i + 1} must be an object, got {type(donor).__name__}")
            continue
        name_obj = donor.get("name")
        if name_obj is not None and not isinstance(name_obj, dict):
            errors.append(f"{p.name}: donor #{i + 1} — 'name' must be an object with a 'hi' key, got {type(name_obj).__name__}")
            continue
        raw_hi = (name_obj or {}).get("hi")
        name = raw_hi if isinstance(raw_hi, str) else None
        who = name or f"donor #{i + 1}"
        if raw_hi is not None and not isinstance(raw_hi, str):
            errors.append(f"{p.name}: donor #{i + 1} — name.hi must be text, got {type(raw_hi).__name__}")
        elif not name:
            errors.append(f"{p.name}: donor #{i + 1} is missing name.hi")
        elif unicodedata.normalize("NFC", name) != name:
            errors.append(f"{p.name}: {who} — name.hi must be NFC normalized")
        if "memoriam" in donor and not isinstance(donor["memoriam"], bool):
            errors.append(f"{p.name}: {who} — 'memoriam' must be true or false")

        items = donor.get("items")
        if not isinstance(items, list):
            errors.append(f"{p.name}: {who} — 'items' must be a list")
            continue
        for j, item in enumerate(items):
            where = f"{p.name}: {who} — item #{j + 1}"
            if not isinstance(item, dict):
                errors.append(f"{where} must be an object, got {type(item).__name__}")
                continue
            code = item.get("type")
            if code not in TYPES:
                errors.append(f"{where} has unknown type {code!r}")
            unit = item.get("unit")
            if unit is not None and unit not in UNITS:
                errors.append(f"{where} has unknown unit {unit!r}")
            if "qty" in item and not _is_number(item["qty"]):
                errors.append(f"{where} — 'qty' must be a finite number, got {item['qty']!r}")
            if "qty" in item and unit is None:
                # The public totals skip any item without a unit, so it would
                # show on the donor's card but silently vanish from the sum.
                errors.append(f"{where} has a 'qty' but no 'unit' — it would be left out of the totals")
    return errors


def read_index(index_path: Path) -> tuple[list[int], list[str]]:
    """Return (years, errors) for donors-index.json. Never raises."""
    name = index_path.name
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"{name}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    except (OSError, UnicodeDecodeError) as exc:
        return [], [f"{name}: cannot read the file ({exc.__class__.__name__}: {exc})"]
    if not isinstance(data, dict) or "years" not in data:
        return [], [f"{name}: must be an object with a 'years' list, like {{\"years\": [2025]}}"]
    years = data["years"]
    if not isinstance(years, list):
        return [], [f"{name}: 'years' must be a list of numbers, like [2025, 2026]"]
    errors = []
    good = []
    for y in years:
        if isinstance(y, str) and y.isdigit():
            errors.append(f"{name}: year \"{y}\" is in quotes - write {y} without quotes")
        elif isinstance(y, bool) or not isinstance(y, int):
            errors.append(f"{name}: 'years' must contain only whole numbers, got {y!r}")
        else:
            good.append(y)
    return good, errors


def check_year_page(site_root: Path, lang: str, year: int) -> list[str]:
    """The page folder must exist AND be about this year (a copied folder
    whose data-year was not updated would publish last year's list)."""
    rel = f"{lang}/daan/{year}/index.html"
    f = site_root / rel
    if not f.is_file():
        return [f"donors-index.json lists {year} but {rel} is missing"]
    try:
        html = f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{rel}: cannot read the file ({exc})"]
    errors = []
    if f'data-year="{year}"' not in html:
        found = re.findall(r'data-year="([^"]*)"', html)
        errors.append(f"{rel}: expected data-year=\"{year}\" but found "
                      f"{', '.join(found) if found else 'no data-year attribute'}"
                      " - the page would show the wrong year's list")
    want = f"/daan/{year}/"
    tags = re.findall(r"<(?:link|meta)\b[^>]*>", html)

    def url_of(tag):
        m = re.search(r'\b(?:href|content)="([^"]*)"', tag)
        return m.group(1) if m else ""

    canon = [url_of(t) for t in tags if re.search(r'rel="canonical"', t)]
    ogurl = [url_of(t) for t in tags if re.search(r'property="og:url"', t)]
    selfhl = [url_of(t) for t in tags if re.search(rf'hreflang="{lang}"', t)]
    for label, urls in (("canonical", canon), ("og:url", ogurl),
                        (f'hreflang="{lang}"', selfhl)):
        if not urls or not all(want in u for u in urls):
            errors.append(f"{rel}: {label} should contain {want} but found "
                          f"{', '.join(urls) if urls else 'nothing'}")
    return errors


def find_list_pages(site_root: Path) -> dict[str, dict[str, str]]:
    """slug -> {lang: page path} for every page carrying data-list="slug"."""
    found: dict[str, dict[str, str]] = {}
    for lang in ("hi", "en"):
        for f in sorted((site_root / lang).rglob("index.html")):
            try:
                html = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for slug in re.findall(r'data-list="([^"]*)"', html):
                found.setdefault(slug, {}).setdefault(lang, f.relative_to(site_root).as_posix())
    return found


def check_named_lists(site_root: Path, data_dir: Path) -> tuple[list[Path], list[str]]:
    """The data files the data-list pages point at, and what is wrong with them."""
    files, errors = [], []
    for slug, pages in sorted(find_list_pages(site_root).items()):
        first = next(iter(pages.values()))
        if not SLUG.match(slug):
            errors.append(f'{first}: data-list="{slug}" is not a plain name like "hanuman-mandir"')
            continue
        for have, missing in (("hi", "en"), ("en", "hi")):
            if have in pages and missing not in pages:
                errors.append(f'data-list="{slug}" has a {have} page but no {missing} page')
        path = data_dir / f"{slug}.json"
        if path.is_file():
            files.append(path)
        else:
            errors.append(f'{first} shows data-list="{slug}" but data/{slug}.json is missing')
    return files, errors


def read_index_lists(index_path: Path) -> tuple[list[str], list[str]]:
    """The named lists in donors-index.json ("lists"); read_index reports bad JSON."""
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [], []
    lists = data.get("lists", []) if isinstance(data, dict) else []
    if not isinstance(lists, list) or not all(isinstance(x, str) for x in lists):
        return [], [f"{index_path.name}: 'lists' must be a list of names, like [\"hanuman-mandir\"]"]
    return lists, []


def _hi(donor) -> object:
    """donor's name.hi, or None when the name or the donor is not an object."""
    name = donor.get("name") if isinstance(donor, dict) else None
    return name.get("hi") if isinstance(name, dict) else None


def check_register(data_dir: Path, list_paths: list[Path]) -> list[str]:
    """data/donors.json is sound and every donorIds value in every list resolves."""
    entries = []
    for path in list_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue                         # validate_file reports it
        for pos, item in enumerate(data.get("donors", []) if isinstance(data, dict) else [], 1):
            if isinstance(item, dict):
                entries.append((path.name, pos, item))

    reg_path = data_dir / "donors.json"
    if not reg_path.exists():
        if any("donorIds" in item for _, _, item in entries):
            return ["data/donors.json is missing but list entries carry donorIds - "
                    "run python3 tools/assign_donor_ids.py"]
        return []
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"donors.json: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    if not isinstance(reg, dict):
        return ['donors.json: must have "donors" and "merged" objects']
    donors, merged = reg.get("donors"), reg.get("merged", {})
    if not isinstance(donors, dict) or not isinstance(merged, dict):
        return ['donors.json: must have "donors" and "merged" objects']

    errors: list[str] = []
    owner: dict[str, str] = {}
    for did, donor in donors.items():
        if not DONOR_ID.match(did):
            errors.append(f"donors.json: {did!r} is not a Donor ID like D0042")
        donor = donor if isinstance(donor, dict) else {}
        name = _hi(donor)
        if not isinstance(name, str) or not name.strip():
            errors.append(f"donors.json: {did} has no name.hi")
        aliases = donor.get("aliases") or []
        if not isinstance(aliases, list):
            errors.append(f"donors.json: {did} has aliases that are not a list")
            aliases = []
        for alias in aliases:
            if not isinstance(alias, str):
                errors.append(f"donors.json: {did} has an alias that is not text: {alias!r}")
                continue
            if alias in owner:
                errors.append(f"donors.json: the spelling {alias!r} belongs to both {owner[alias]} and {did}")
            owner[alias] = did
    for old in [k for k, v in merged.items() if not isinstance(v, str)]:
        errors.append(f"donors.json: {old} is merged into {merged.pop(old)!r}, which is not a Donor ID")
    for old, target in merged.items():
        if old in donors:
            errors.append(f"donors.json: {old} is merged into {target} but is still listed as a donor")
        if target not in donors:
            errors.append(f"donors.json: {old} is merged into {target}, which is not a donor")

    def resolves(did):
        return did in donors or merged.get(did) in donors

    distinct = reg.get("distinct", [])
    if not isinstance(distinct, list):
        errors.append('donors.json: "distinct" must be a list of pairs')
        distinct = []
    for pair in distinct:
        if not isinstance(pair, list):
            errors.append(f'donors.json: a "distinct" entry must be a list of two IDs, got {pair!r}')
            continue
        for did in pair:
            if not isinstance(did, str) or not resolves(did):
                errors.append(f'donors.json: "distinct" names {did}, which is not a donor')
    used: set[str] = set()
    pins = reg.get("pins", {})
    if pins is None:
        pins = {}
    if not isinstance(pins, dict):
        errors.append('donors.json: "pins" must be an object')
        pins = {}
    for ref, pin in pins.items():
        if not isinstance(pin, dict):
            errors.append(f"donors.json: pin {ref} must be an object with donorIds")
            continue
        pin_ids = pin.get("donorIds", [])
        if not isinstance(pin_ids, list):
            errors.append(f"donors.json: pin {ref} has donorIds that are not a list")
            continue
        for did in pin_ids:
            if isinstance(did, str) and resolves(did):
                used.add(did if did in donors else merged.get(did))
            else:
                errors.append(f"donors.json: pin {ref} names {did}, which is not a donor")
    for fname, pos, item in entries:
        name = item.get("name")
        who = name.get("hi", f"#{pos}") if isinstance(name, dict) else f"#{pos}"
        ids = item.get("donorIds")
        if not isinstance(ids, list):
            errors.append(f"{fname}: entry #{pos} ({who}) has no donorIds - "
                          f"run python3 tools/assign_donor_ids.py")
            continue
        for did in ids:
            if isinstance(did, str) and resolves(did):
                used.add(did if did in donors else merged.get(did))
            else:
                errors.append(f"{fname}: entry #{pos} ({who}) names {did!r}, which is not in data/donors.json")
    for did in sorted(set(donors) - used):
        name = _hi(donors[did]) or ""
        errors.append(f"donors.json: {did} ({name}) is not used by any list entry")
    return errors


def main(argv: list[str], data_dir: Path | None = None,
         site_root: Path | None = None) -> int:
    if data_dir is None:
        root = Path(__file__).resolve().parent.parent
        data_dir = root / "data"
    if site_root is None:
        site_root = data_dir.parent
    paths = ([Path(a) for a in argv[1:]]
             or sorted(data_dir.glob("donors-[0-9][0-9][0-9][0-9].json")))

    index_path = data_dir / "donors-index.json"
    all_errors: list[str] = []
    # NB: the glob above deliberately matches only donors-YYYY.json, never
    # donors-index.json, which is not a donor file.
    for path in paths:
        all_errors.extend(validate_file(str(path)))

    if index_path.exists() and not argv[1:]:
        years, index_errors = read_index(index_path)
        all_errors.extend(index_errors)
        listed = set(years)
        on_disk = {int(re.search(r"(\d{4})", p.name).group(1)) for p in paths}
        if not index_errors:
            for year in sorted(listed - on_disk):
                all_errors.append(f"donors-index.json lists {year} but data/donors-{year}.json is missing")
            for year in sorted(on_disk - listed):
                all_errors.append(f"data/donors-{year}.json exists but donors-index.json does not list it")
        # check_links.py cannot see these links: the archive page builds them
        # in JavaScript from the index at runtime. So check the pages here.
        for year in sorted(listed):
            for lang in ("hi", "en"):
                all_errors.extend(check_year_page(site_root, lang, year))

    if not argv[1:]:
        list_files, list_errors = check_named_lists(site_root, data_dir)
        all_errors.extend(list_errors)
        for path in list_files:
            all_errors.extend(validate_file(str(path)))
        paths = paths + list_files
        all_errors.extend(check_register(data_dir, paths))
        if index_path.exists():
            index_lists, list_index_errors = read_index_lists(index_path)
            all_errors.extend(list_index_errors)
            on_pages = set(find_list_pages(site_root))
            for slug in sorted(on_pages - set(index_lists)):
                all_errors.append(f'data-list="{slug}" pages exist but donors-index.json "lists" does not name it')
            for slug in sorted(set(index_lists) - on_pages):
                all_errors.append(f'donors-index.json "lists" names {slug} but no page shows data-list="{slug}"')

    for error in all_errors:
        print(error)
    print(f"\n{len(paths)} file(s) checked, {len(all_errors)} error(s)")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
