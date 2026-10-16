#!/usr/bin/env python3
"""Write the donor counts into data/donors-index.json.

The दान page prints "2026 · 50 दानदाता" beside each list. Counting there would
mean fetching all six donor files (hundreds of kilobytes) to show six numbers,
so the count is written here instead, next to the names the page already
reads. Run after adding or editing a list; tools/test_donor_index_counts.py
fails if the file and the count disagree.

Usage: python3 tools/update_donor_index.py [--check]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def counts(index: dict) -> dict[str, int]:
    """{list name -> donors in its file}, in the index's own order."""
    out = {}
    for year in index["years"]:
        out[str(year)] = len(json.loads((DATA / f"donors-{year}.json")
                                        .read_text(encoding="utf-8"))["donors"])
    for slug in index["lists"]:
        out[slug] = len(json.loads((DATA / f"{slug}.json")
                                   .read_text(encoding="utf-8"))["donors"])
    return out


def main(argv: list[str]) -> int:
    path = DATA / "donors-index.json"
    index = json.loads(path.read_text(encoding="utf-8"))
    fresh = counts(index)
    if index.get("counts") == fresh:
        print(f"donors-index.json: counts already current ({sum(fresh.values())} entries)")
        return 0
    if "--check" in argv:
        print(f"donors-index.json: counts are stale\n  file says {index.get('counts')}\n"
              f"  lists hold {fresh}")
        return 1
    index["counts"] = fresh
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"donors-index.json: counts written ({sum(fresh.values())} entries across "
          f"{len(fresh)} list(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
