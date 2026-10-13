"""The temple list's own spellings, on lines copied from the source (which lives
outside the repo). The receipt notes are the समाज's own record of who has paid;
the public page must not show them, so none may survive into the output."""
import json

import pytest

import convert_hanuman_mandir as c


def test_bold_name_role_and_cement_bags():
    assert c.parse_line("**श्री धन्नालाल जाट** (पूर्व उपाध्यक्ष, लोधा समाज) — 551 ईंट", 1) == {
        "name": {"hi": "श्री धन्नालाल जाट (पूर्व उपाध्यक्ष, लोधा समाज)"},
        "items": [{"type": "brick", "qty": 551, "unit": "count"}]}
    assert c.parse_line("**श्री मोहन जाट (M×R)** — 21 बोरी सीमेंट", 2)["items"] == [
        {"type": "cement", "qty": 21, "unit": "bag"}]


@pytest.mark.parametrize("contribution", [
    "₹1,100 नकद प्राप्त", "₹1,100 ऑनलाइन प्राप्त", "₹1,100"])
def test_receipt_notes_are_dropped(contribution):
    donor = c.parse_line(f"**श्री क** — {contribution}", 5)
    assert donor["items"] == [{"type": "cash", "qty": 1100, "unit": "inr"}]
    assert "प्राप्त" not in json.dumps(donor, ensure_ascii=False)


def test_material_received_note_is_dropped_and_rebar_is_by_weight():
    assert c.parse_line("**श्री अजय जमदार** — 51 किलोग्राम सरिया, सामग्री प्राप्त", 14)["items"] == [
        {"type": "rebar", "qty": 51, "unit": "kg"}]
    assert c.parse_line("**श्री क** — 5 बोरी सीमेंट, सामग्री प्राप्त", 13)["items"] == [
        {"type": "cement", "qty": 5, "unit": "bag"}]


def test_a_dash_inside_the_bold_name_is_part_of_the_name():
    donor = c.parse_line("**गुप्त दान — जय श्री राम** — 10 बोरी सीमेंट, सामग्री प्राप्त", 44)
    assert donor["name"]["hi"] == "गुप्त दान — जय श्री राम"


def test_an_unknown_word_is_an_error_not_a_drop():
    with pytest.raises(ValueError, match="cannot account for"):
        c.parse_line("**श्री क** — 5 बोरी सीमेंट बढ़िया", 1)


def test_build_numbers_without_gaps_and_reports_death_markers_without_ruling():
    lines = ["1. **स्वर्गीय श्री क एवं श्री ख** — ₹501 नकद प्राप्त",
             "2. **श्री ग** — 2 बोरी सीमेंट"]
    donors, death_marked = c.build(c.read_rows("\n".join(lines)))
    assert len(donors) == 2
    assert not any(d.get("memoriam") for d in donors)
    assert death_marked == ["  #1: स्वर्गीय श्री क एवं श्री ख"]
    with pytest.raises(ValueError, match="without gaps"):
        c.build(c.read_rows("1. **श्री क** — ₹1\n3. **श्री ख** — ₹1"))


def test_an_edited_override_row_fails_loudly():
    rows = [(n, f"**श्री {n}** — ₹1") for n in range(1, 30)]
    rows.append((30, "**श्री मन्नूलाल जी वर्मा** — टाइल्स"))
    with pytest.raises(ValueError, match="Re-review that ruling"):
        c.build(rows)
