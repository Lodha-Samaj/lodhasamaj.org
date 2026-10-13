"""The 2024 list's own spellings: commas between items, plural tins, gas by the
cylinder and grouped rupee amounts. The source itself lives outside the repo,
so these test the parser on lines copied from it."""
import pytest

import convert_2024_md as c


def test_grouped_rupees_with_and_without_naqad():
    assert c.parse_items("₹1,000 नगद", 1) == [{"type": "cash", "qty": 1000, "unit": "inr"}]
    assert c.parse_items("₹5,100", 1) == [{"type": "cash", "qty": 5100, "unit": "inr"}]


def test_items_split_on_comma_space_but_not_inside_an_amount():
    assert c.parse_items("500 किलो शक्कर, 31 किलो नमक", 10) == [
        {"type": "sugar", "qty": 500, "unit": "kg"},
        {"type": "salt", "qty": 31, "unit": "kg"}]


def test_plural_tins_ghee_and_gas_cylinders():
    assert c.parse_items("5 डब्बे तेल", 3) == [{"type": "oil", "qty": 5, "unit": "tin"}]
    assert c.parse_items("2 डब्बे शुद्ध देसी घी", 120) == [{"type": "ghee", "qty": 2, "unit": "tin"}]
    assert c.parse_items("5 गैस सिलेंडर", 109) == [{"type": "gas", "qty": 5, "unit": "cylinder"}]


def test_an_unknown_word_is_an_error_not_a_drop():
    with pytest.raises(ValueError, match="cannot account for"):
        c.parse_items("51 किलो शक्कर बढ़िया", 1)


def test_repeated_rows_and_death_markers_are_reported_not_ruled_on():
    rows = [(1, "स्व. श्री क — 51 किलो आटा"),
            (2, "श्री ख — 51 किलो शक्कर"),
            (3, "श्री ख — 51 किलो शक्कर")]
    donors, death_marked, repeats = c.build(rows)
    assert len(donors) == 3
    assert not any(d.get("memoriam") for d in donors)
    assert death_marked == ["  #1: स्व. श्री क"]
    assert repeats == ["  #2 = #3: श्री ख — 51 किलो शक्कर"]


def test_an_edited_override_row_fails_loudly():
    rows = [(n, f"श्री {n} — 1 डब्बा तेल") for n in range(1, 121)]
    rows.append((121, "श्री मनोहर जी वर्मा — केले के पत्ते"))
    with pytest.raises(ValueError, match="Re-review that ruling"):
        c.build(rows)
