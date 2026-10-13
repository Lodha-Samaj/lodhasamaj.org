"""Donor IDs: splitting names into people, and the keys used to match them."""
import json

import pytest

import assign_donor_ids as a


def texts(name):
    return [p["text"] for p in a.split_people(name)]


def test_joint_names_split_on_evam_aur_and_commas_but_not_inside_brackets():
    assert texts("श्री संजू जाट एवं श्री कमल जाट") == ["श्री संजू जाट", "श्री कमल जाट"]
    assert texts("श्री कृष्णा मंझे, श्री शंकर जाट एवं श्री राजा राज") == [
        "श्री कृष्णा मंझे", "श्री शंकर जाट", "श्री राजा राज"]
    assert texts("श्री धन्नालाल जाट (पूर्व उपाध्यक्ष, लोधा समाज)") == [
        "श्री धन्नालाल जाट (पूर्व उपाध्यक्ष, लोधा समाज)"]


def test_a_second_shri_starts_a_second_person_unless_tied_to_the_first():
    assert texts("श्री राजू जी जाट श्री मोहन जी जाट (MxR मंडी)") == [
        "श्री राजू जी जाट", "श्री मोहन जी जाट (MxR मंडी)"]
    assert texts("पंडित श्री मनोज जी उपाध्याय") == ["पंडित श्री मनोज जी उपाध्याय"]
    assert texts("स्व. श्रीमती कुंदन बाई के पुत्र श्री गोलू जी लोवंशी (दिल्ली) की ओर से") == [
        "स्व. श्रीमती कुंदन बाई के पुत्र श्री गोलू जी लोवंशी (दिल्ली) की ओर से"]


def test_a_memorial_in_a_joint_entry_gets_no_id_but_a_sole_memorial_does():
    assert texts("स्वर्गीय श्री मुकेश भवानी एवं श्री सिकंदर भवानी") == ["श्री सिकंदर भवानी"]
    assert texts("स्व. श्री भोजराज जी पटेल श्री प्रकाश जी पटेल") == ["श्री प्रकाश जी पटेल"]
    sole = a.split_people("स्व. श्री मुकेश भवानी")
    assert sole == [{"text": "स्व. श्री मुकेश भवानी", "memorial": True}]


def test_family_stays_with_its_person_and_anonymous_gifts_have_no_people():
    assert texts("अमित जी राजपूत एवं परिवार") == ["अमित जी राजपूत एवं परिवार"]
    assert texts("स्व. किशोरी जी मंझे का परिवार") == ["स्व. किशोरी जी मंझे का परिवार"]
    assert a.split_people("गुप्त दान — जय श्री राम") == []


def test_keys_set_aside_honorifics_and_places_but_never_change_spelling():
    assert a.strict_key("श्री विक्रम जी जाट (उपाध्यक्ष, लोधा समाज)") == "विक्रम जाट"
    assert a.strict_key("श्री अजय कोतुल") != a.strict_key("श्री अजय जी कौतूल")
    assert a.loose_key("श्री अजय कोतुल") == a.loose_key("श्री अजय जी कौतूल")
    assert a.loose_key("श्री शेखर मंझे") == a.loose_key("श्री शेखर जी मंजे")
    assert a.loose_key("श्री राधे जामदार") == a.loose_key("श्री राधे जमदार")
    assert a.loose_key("स्व. किशोरी जी मंझे का परिवार") == a.loose_key("स्व. श्री किशोरी जी मंजे")


def test_places_agree_when_absent_or_contained():
    assert a.place_of("श्री विक्रम जाट (उपाध्यक्ष, लोधा समाज)") == "उपाध्यक्ष, लोधा समाज"
    assert a.places_compatible("", "दिल्ली")
    assert a.places_compatible("उपाध्यक्ष, लोधा समाज", "उपाध्यक्ष, लोधा समाज इंदौर")
    assert not a.places_compatible("दिल्ली", "महू")


def entry(name, **extra):
    return {"name": {"hi": name}, "items": [{"type": "cash", "qty": 1, "unit": "inr"}], **extra}


def lists_of(**named):
    return [(key, {"donors": [entry(n) for n in names]}) for key, names in named.items()]


def ids(lists, key):
    return [e["donorIds"] for k, d in lists if k == key for e in d["donors"]]


def test_same_name_across_lists_gets_one_id_and_every_spelling_is_kept():
    reg = a.new_register()
    lists = lists_of(**{"2024": ["श्री विक्रम जाट (उपाध्यक्ष, लोधा समाज)"],
                        "2025": ["श्री विक्रम जी जाट (उपाध्यक्ष, लोधा समाज इंदौर)"]})
    a.assign(reg, lists)
    assert ids(lists, "2024") == [["D0001"]] and ids(lists, "2025") == [["D0001"]]
    assert reg["donors"]["D0001"]["aliases"] == [
        "श्री विक्रम जाट (उपाध्यक्ष, लोधा समाज)", "श्री विक्रम जी जाट (उपाध्यक्ष, लोधा समाज इंदौर)"]


def test_conflicting_places_spelling_variants_and_memorial_status_are_never_linked():
    reg = a.new_register()
    lists = lists_of(**{"2024": ["श्री शिव भवानी (दिल्ली)", "श्री अजय कोतुल", "स्व. श्री कैलाश चौधरी"],
                        "2025": ["श्री शिव भवानी (महू)", "श्री अजय जी कौतूल", "श्री कैलाश चौधरी"]})
    a.assign(reg, lists)
    assert ids(lists, "2024") == [["D0001"], ["D0002"], ["D0003"]]
    assert ids(lists, "2025") == [["D0004"], ["D0005"], ["D0006"]]


def test_joint_entries_carry_one_id_per_person_and_anonymous_none():
    reg = a.new_register()
    lists = lists_of(**{"2025": ["श्री संजू जी जाट श्री कमल जी जाट"],
                        "hanuman-mandir": ["श्री संजू जाट एवं श्री कमल जाट", "गुप्त दान — जय श्री राम"]})
    a.assign(reg, lists)
    assert ids(lists, "2025") == [["D0001", "D0002"]]
    assert ids(lists, "hanuman-mandir") == [["D0001", "D0002"], []]


def test_donor_ids_sit_right_after_the_name():
    reg = a.new_register()
    lists = lists_of(**{"2025": ["श्री क"]})
    a.assign(reg, lists)
    assert list(lists[0][1]["donors"][0]) == ["name", "donorIds", "items"]


def test_existing_ids_are_reused_and_new_ones_continue_after_merged_ids():
    reg = a.new_register()
    reg["donors"]["D0007"] = {"name": {"hi": "श्री क"}, "aliases": ["श्री क"]}
    reg["merged"]["D0009"] = "D0007"
    lists = lists_of(**{"2026": ["श्री क", "श्री ख"]})
    a.assign(reg, lists)
    assert ids(lists, "2026") == [["D0007"], ["D0010"]]
    assert a.resolve(reg, "D0009") == "D0007" and a.resolve(reg, "D0999") is None


def test_rename_uses_the_last_spelling_unless_the_name_is_fixed():
    reg = a.new_register()
    lists = lists_of(**{"2024": ["श्री विक्रम जाट"], "2025": ["श्री विक्रम जी जाट"]})
    a.rename(reg, a.assign(reg, lists))
    assert reg["donors"]["D0001"]["name"] == {"hi": "श्री विक्रम जी जाट"}
    reg["donors"]["D0001"].update(name={"hi": "श्री विक्रम जाट", "en": "Vikram Jat"}, fixedName=True)
    a.rename(reg, a.assign(reg, lists))
    assert reg["donors"]["D0001"]["name"] == {"hi": "श्री विक्रम जाट", "en": "Vikram Jat"}


def test_a_pin_is_applied_as_is_and_a_changed_list_stops_the_run():
    reg = a.new_register()
    reg["donors"]["D0001"] = {"name": {"hi": "श्री अजय जाट"}, "aliases": ["श्री अजय जाट"]}
    reg["donors"]["D0002"] = {"name": {"hi": "श्री अजय जाट"}, "aliases": []}
    reg["pins"]["2024#2"] = {"name": "श्री अजय जाट", "donorIds": ["D0002"]}
    lists = lists_of(**{"2024": ["श्री अजय जाट", "श्री अजय जाट"]})
    a.assign(reg, lists)
    assert ids(lists, "2024") == [["D0001"], ["D0002"]]
    changed = lists_of(**{"2024": ["श्री अजय जाट", "श्री विजय जाट"]})
    with pytest.raises(ValueError, match="pinned"):
        a.assign(reg, changed)
