"""Drift guard: data/donors-index.json carries how many donors each list has,
so the दान page can print the number without fetching six donor files. The
counts are written by tools/update_donor_index.py; this fails when a list is
edited and the tool is not re-run."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INDEX = json.loads((DATA / "donors-index.json").read_text(encoding="utf-8"))


def donors_in(path: Path) -> int:
    return len(json.loads(path.read_text(encoding="utf-8"))["donors"])


def test_every_list_in_the_index_has_a_count():
    want = {str(year) for year in INDEX["years"]} | set(INDEX["lists"])
    assert set(INDEX.get("counts", {})) == want, (
        f"counts cover {sorted(INDEX.get('counts', {}))}, the index lists {sorted(want)}")


def test_each_count_is_what_the_file_holds():
    for year in INDEX["years"]:
        assert INDEX["counts"][str(year)] == donors_in(DATA / f"donors-{year}.json"), year
    for slug in INDEX["lists"]:
        assert INDEX["counts"][slug] == donors_in(DATA / f"{slug}.json"), slug


def test_the_counts_add_up_to_every_entry_on_the_site():
    total = sum(INDEX["counts"].values())
    on_disk = sum(donors_in(DATA / f"donors-{y}.json") for y in INDEX["years"]) \
        + sum(donors_in(DATA / f"{s}.json") for s in INDEX["lists"])
    assert total == on_disk
