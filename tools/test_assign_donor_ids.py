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


def assigned(**named):
    reg = a.new_register()
    lists = lists_of(**named)
    a.rename(reg, a.assign(reg, lists))
    return reg, lists


def test_review_suggests_spelling_place_and_memorial_pairs_with_reasons():
    reg, lists = assigned(**{"2024": ["श्री अजय कोतुल", "श्री शिव भवानी (दिल्ली)", "स्व. श्री कैलाश चौधरी"],
                             "2025": ["श्री अजय जी कौतूल", "श्री शिव भवानी (महू)", "श्री कैलाश चौधरी"]})
    reasons = {(i["a"]["id"], i["b"]["id"]): i["reason"] for i in a.review_items(reg, lists)}
    assert reasons == {("D0001", "D0004"): "spelling: अजय कोतुल / अजय कौतूल",
                       ("D0002", "D0005"): "same name, different place",
                       ("D0003", "D0006"): "one name is स्वर्गीय"}
    item = a.review_items(reg, lists)[0]
    assert item["a"] == {"id": "D0001", "name": "श्री अजय कोतुल", "lists": ["2024"]}
    assert item["same"] is None


def test_review_reports_the_same_name_twice_in_one_list():
    reg, lists = assigned(**{"2024": ["श्री अजय जाट", "श्री ख", "श्री अजय जाट"]})
    [item] = a.review_items(reg, lists)
    assert item == {"kind": "repeat", "id": "D0001", "name": "श्री अजय जाट", "list": "2024",
                    "entries": [{"ref": "2024#1", "name": "श्री अजय जाट"},
                                {"ref": "2024#3", "name": "श्री अजय जाट"}],
                    "reason": "same name twice in one list", "same": None}


def answer(items, same):
    return [{**i, "same": same} for i in items]


def test_true_merges_keeping_the_lower_id_and_old_ids_redirect():
    reg, lists = assigned(**{"2024": ["श्री अजय कोतुल"], "2025": ["श्री अजय जी कौतूल"]})
    assert a.apply_answers(reg, answer(a.review_items(reg, lists), True), lists) == 1
    a.assign(reg, lists)
    assert ids(lists, "2024") == ids(lists, "2025") == [["D0001"]]
    assert reg["merged"] == {"D0002": "D0001"}
    assert reg["donors"]["D0001"]["aliases"] == ["श्री अजय कोतुल", "श्री अजय जी कौतूल"]
    assert a.review_items(reg, lists) == []


def test_false_is_remembered_and_never_asked_again():
    reg, lists = assigned(**{"2024": ["श्री अजय कोतुल"], "2025": ["श्री अजय जी कौतूल"]})
    a.apply_answers(reg, answer(a.review_items(reg, lists), False), lists)
    assert reg["distinct"] == [["D0001", "D0002"]]
    assert a.review_items(reg, lists) == []


def test_repeat_true_is_remembered_and_repeat_false_pins_a_new_id():
    reg, lists = assigned(**{"2024": ["श्री अजय जाट", "श्री अजय जाट"]})
    keep = a.review_items(reg, lists)
    a.apply_answers(reg, answer(keep, True), lists)
    assert reg["sameInList"] == ["2024:D0001"] and a.review_items(reg, lists) == []

    reg, lists = assigned(**{"2024": ["श्री अजय जाट", "श्री अजय जाट"]})
    a.apply_answers(reg, answer(a.review_items(reg, lists), False), lists)
    a.assign(reg, lists)
    assert ids(lists, "2024") == [["D0001"], ["D0002"]]
    assert reg["pins"] == {"2024#1": {"name": "श्री अजय जाट", "donorIds": ["D0001"]},
                           "2024#2": {"name": "श्री अजय जाट", "donorIds": ["D0002"]}}
    assert reg["ambiguous"] == ["श्री अजय जाट"]


@pytest.mark.parametrize("bad", ["हाँ", "yes", 1, 0, "true"])
def test_an_answer_other_than_true_false_or_null_stops_with_a_plain_message(bad):
    reg, lists = assigned(**{"2024": ["श्री अजय कोतुल"], "2025": ["श्री अजय जी कौतूल"]})
    with pytest.raises(ValueError, match="write true, false or null"):
        a.apply_answers(reg, answer(a.review_items(reg, lists), bad), lists)


def test_merge_repoints_earlier_merges_distinct_pairs_and_pins():
    reg = a.new_register()
    for did in ("D0001", "D0002", "D0003"):
        reg["donors"][did] = {"name": {"hi": did}, "aliases": [did]}
    reg["merged"]["D0009"] = "D0003"
    reg["distinct"] = [["D0002", "D0003"]]
    reg["pins"]["2024#4"] = {"name": "x", "donorIds": ["D0003"]}
    a.merge(reg, "D0003", "D0001")
    assert reg["merged"] == {"D0009": "D0001", "D0003": "D0001"}
    assert reg["distinct"] == [["D0001", "D0002"]]
    assert reg["pins"]["2024#4"]["donorIds"] == ["D0001"]


def site(tmp_path, index, files):
    data = tmp_path / "data"
    data.mkdir()
    (data / "donors-index.json").write_text(json.dumps(index), encoding="utf-8")
    for name, names in files.items():
        (data / name).write_text(json.dumps({"donors": [entry(n) for n in names]},
                                            ensure_ascii=False), encoding="utf-8")
    return data, tmp_path / "docs" / "donor-review.json"


def snapshot(tmp_path):
    return {p.relative_to(tmp_path).as_posix(): p.read_bytes()
            for p in sorted(tmp_path.rglob("*.json"))}


def test_a_second_run_changes_nothing(tmp_path):
    data, review = site(tmp_path, {"years": [2024], "lists": ["hanuman-mandir"]},
                        {"donors-2024.json": ["श्री अजय कोतुल", "श्री क"],
                         "hanuman-mandir.json": ["श्री अजय जी कौतूल", "श्री क"]})
    a.run(data, review)
    first = snapshot(tmp_path)
    a.run(data, review)
    assert snapshot(tmp_path) == first
    assert json.loads(review.read_text(encoding="utf-8"))[0]["reason"].startswith("spelling")


def test_a_reconverted_list_gets_its_ids_back(tmp_path):
    data, review = site(tmp_path, {"years": [2024, 2025]},
                        {"donors-2024.json": ["श्री क"], "donors-2025.json": ["श्री ख", "श्री क"]})
    a.run(data, review)
    before = (data / "donors-2025.json").read_text(encoding="utf-8")
    (data / "donors-2025.json").write_text(json.dumps(
        {"donors": [entry("श्री ख"), entry("श्री क")]}, ensure_ascii=False), encoding="utf-8")
    a.run(data, review)
    assert (data / "donors-2025.json").read_text(encoding="utf-8") == before


def test_answers_in_the_review_file_are_applied_and_leave_it(tmp_path):
    data, review = site(tmp_path, {"years": [2024, 2025]},
                        {"donors-2024.json": ["श्री अजय कोतुल"], "donors-2025.json": ["श्री अजय जी कौतूल"]})
    a.run(data, review)
    items = json.loads(review.read_text(encoding="utf-8"))
    review.write_text(json.dumps(answer(items, True), ensure_ascii=False), encoding="utf-8")
    assert a.run(data, review)["applied"] == 1
    assert json.loads(review.read_text(encoding="utf-8")) == []
    register = json.loads((data / "donors.json").read_text(encoding="utf-8"))
    assert list(register) == ["donors", "merged", "distinct", "sameInList", "pins", "ask",
                              "ambiguous"]
    assert register["merged"] == {"D0002": "D0001"}


def test_check_writes_nothing_and_a_bad_answer_fails_without_writing(tmp_path, capsys):
    data, review = site(tmp_path, {"years": [2024]}, {"donors-2024.json": ["श्री क"]})
    a.run(data, review, write=False)
    assert not (data / "donors.json").exists()
    review.parent.mkdir()
    review.write_text('[{"kind": "pair", "a": {"id": "D0001"}, "b": {"id": "D0002"}, "same": "हाँ"}]',
                      encoding="utf-8")
    with pytest.raises(ValueError, match="write true, false or null"):
        a.run(data, review)
    assert not (data / "donors.json").exists()


def test_loose_key_ignores_family_and_joiner_words():
    assert a.loose_key("अमित जी राजपूत एवं परिवार") == a.loose_key("श्री अमित जी राजपूत (महाराष्ट्र)")


def test_family_wording_is_suggested_for_review_not_linked():
    reg, lists = assigned(**{"2024": ["अमित जी राजपूत एवं परिवार"],
                             "2025": ["श्री अमित जी राजपूत (महाराष्ट्र)"]})
    [item] = a.review_items(reg, lists)
    assert item["reason"] == "family wording: अमित राजपूत एवं परिवार / अमित राजपूत"
    assert ids(lists, "2024") != ids(lists, "2025")


# ---- final-review fixes ----

def test_place_and_memorial_status_are_judged_against_every_alias_of_a_donor():
    reg = a.new_register()
    reg["donors"]["D0001"] = {"name": {"hi": "श्री सुरेश राजपूत"},
                              "aliases": ["श्री सुरेश राजपूत (दिल्ली)", "श्री सुरेश राजपूत"]}
    lists = lists_of(**{"2026": ["श्री सुरेश राजपूत (महू)"]})
    a.assign(reg, lists)
    assert ids(lists, "2026") == [["D0002"]]
    reasons = {(i["a"]["id"], i["b"]["id"]): i["reason"] for i in a.review_items(reg, lists)}
    assert reasons == {("D0001", "D0002"): "same name, different place"}


def test_a_memorial_alias_anywhere_on_a_donor_keeps_a_living_namesake_apart():
    reg = a.new_register()
    reg["donors"]["D0001"] = {"name": {"hi": "श्री कैलाश चौधरी"},
                              "aliases": ["स्व. श्री कैलाश चौधरी", "श्री कैलाश चौधरी (महू)"]}
    lists = lists_of(**{"2026": ["श्री कैलाश जी चौधरी"]})
    a.assign(reg, lists)
    assert ids(lists, "2026") == [["D0002"]]
    reasons = {(i["a"]["id"], i["b"]["id"]): i["reason"] for i in a.review_items(reg, lists)}
    assert reasons == {("D0001", "D0002"): "one name is स्वर्गीय"}


def test_a_family_only_part_rejoins_with_the_separator_printed():
    assert a.split_people("स्व. श्री भारत जी मंजे के परिवार की और से") == [
        {"text": "स्व. श्री भारत जी मंजे के परिवार की और से", "memorial": True}]
    assert texts("अमित जी राजपूत और परिवार") == ["अमित जी राजपूत और परिवार"]
    assert texts("अमित जी राजपूत, परिवार") == ["अमित जी राजपूत, परिवार"]
    assert texts("श्री संजू जाट एवं परिवार और श्री कमल जाट") == [
        "श्री संजू जाट एवं परिवार", "श्री कमल जाट"]


def test_joint_names_without_a_second_shri_are_split():
    assert texts("श्री कलवा जी जमदार आशीष जी जमदार") == ["श्री कलवा जी जमदार", "आशीष जी जमदार"]
    assert texts("स्व. श्री श्याम जी जमदार नितिन जी जमदार") == ["नितिन जी जमदार"]
    assert texts("श्री कालू हजारीलाल जी जमदार") == ["श्री कालू हजारीलाल जी जमदार"]


def test_a_repeated_surname_also_marks_a_second_person():
    assert texts("स्वर्गीय आदित्य जी जमदार रंजीत जमदार") == ["रंजीत जमदार"]
    assert texts("स्व. श्री शेखर कोतवाल ओम जी कोतवाल") == ["ओम जी कोतवाल"]


def test_no_split_inside_one_persons_relations_or_before_a_place():
    assert texts("श्री मोहन जी जाट (MxR मंडी) के पुत्र राजू जी जाट") == [
        "श्री मोहन जी जाट (MxR मंडी) के पुत्र राजू जी जाट"]
    assert texts("श्री लोधा राम लोधा") == ["श्री लोधा राम लोधा"]


def test_places_ignore_punctuation_and_compare_whole_words():
    assert a.places_compatible("कोषाध्यक्ष: लोधा समाज, इंदौर", "कोषाध्यक्ष लोधा समाज इंदौर")
    assert a.places_compatible("उपाध्यक्ष; लोधा समाज.", "उपाध्यक्ष, लोधा  समाज इंदौर")
    assert not a.places_compatible("महू", "महूगांव")
    assert not a.places_compatible("समाज लोधा", "लोधा समाज")


def test_acharya_and_doctor_are_set_aside_in_the_loose_key_only():
    assert a.loose_key("आचार्य मनोज उपाध्याय") == a.loose_key("पंडित श्री मनोज जी उपाध्याय")
    assert a.loose_key("डॉ. सेठिया") == a.loose_key("श्री सेठिया")
    assert a.strict_key("आचार्य मनोज उपाध्याय") != a.strict_key("पंडित श्री मनोज जी उपाध्याय")
    assert a.strict_key("डॉ. सेठिया") == "डॉ. सेठिया"


def test_merge_keeps_the_hand_set_english_name_and_fixed_name():
    reg = a.new_register()
    reg["donors"]["D0001"] = {"name": {"hi": "श्री क"}, "aliases": ["श्री क"]}
    reg["donors"]["D0002"] = {"name": {"hi": "श्री क जी", "en": "Ka"}, "aliases": ["श्री क जी"]}
    a.merge(reg, "D0001", "D0002")
    assert reg["donors"]["D0001"]["name"] == {"hi": "श्री क", "en": "Ka"}
    assert "fixedName" not in reg["donors"]["D0001"]

    reg["donors"]["D0003"] = {"name": {"hi": "श्री क (महू)"}, "aliases": ["श्री क (महू)"],
                              "fixedName": True}
    a.merge(reg, "D0003", "D0001")
    assert reg["donors"]["D0001"]["name"] == {"hi": "श्री क (महू)", "en": "Ka"}
    assert reg["donors"]["D0001"]["fixedName"] is True


def test_a_name_with_an_extra_word_is_suggested_for_review_not_linked():
    reg, lists = assigned(**{"2025": ["श्री कालू हजारीलाल जी जमदार"],
                             "hanuman-mandir": ["श्री कालू जमदार"]})
    assert ids(lists, "2025") == [["D0001"]] and ids(lists, "hanuman-mandir") == [["D0002"]]
    [item] = a.review_items(reg, lists)
    assert (item["a"]["id"], item["b"]["id"]) == ("D0001", "D0002")
    assert item["reason"] == "name with an extra word: कालू हजारीलाल जमदार / कालू जमदार"


def test_an_extra_word_needs_the_same_given_name_and_surname():
    reg, lists = assigned(**{"2025": ["श्री कालू जमदार", "श्री कमल जमदार",
                                      "श्री कालू हजारीलाल जाट"]})
    assert a.review_items(reg, lists) == []


def test_ask_pairs_are_posed_until_answered():
    reg, lists = assigned(**{"2024": ["श्री प्रदीप वर्मा"], "2025": ["श्री राम जाट", "श्री श्याम जाट"]})
    assert reg["ask"] == []
    reg["ask"] = [["D0001", "D0003"], ["D0002", "D0003"]]
    reg["distinct"] = [["D0002", "D0003"]]
    [item] = a.review_items(reg, lists)
    assert item == {"kind": "pair", "a": {"id": "D0001", "name": "श्री प्रदीप वर्मा", "lists": ["2024"]},
                    "b": {"id": "D0003", "name": "श्री श्याम जाट", "lists": ["2025"]},
                    "reason": "asked by the samaj", "same": None}
    a.apply_answers(reg, answer([item], False), lists)
    assert reg["ask"] == [["D0002", "D0003"]] and ["D0001", "D0003"] in reg["distinct"]
    assert a.review_items(reg, lists) == []


def test_an_ask_answered_true_merges_and_leaves_the_list():
    reg, lists = assigned(**{"2024": ["श्री प्रदीप वर्मा"], "2025": ["श्री राम जाट"]})
    reg["ask"] = [["D0001", "D0002"]]
    a.apply_answers(reg, answer(a.review_items(reg, lists), True), lists)
    assert reg["ask"] == [] and reg["merged"] == {"D0002": "D0001"}
    assert a.review_items(reg, lists) == []


def test_merge_repoints_ask_pairs_and_drops_self_pairs():
    reg = a.new_register()
    for did in ("D0001", "D0002", "D0003"):
        reg["donors"][did] = {"name": {"hi": did}, "aliases": [did]}
    reg["ask"] = [["D0001", "D0003"], ["D0002", "D0003"]]
    a.merge(reg, "D0003", "D0001")
    assert reg["ask"] == [["D0001", "D0002"]]


@pytest.mark.parametrize("bad", ["D0001 D0002", [["D0001"]], [["D0001", 2]]])
def test_a_malformed_ask_list_stops_with_a_plain_message(tmp_path, bad):
    data, review = site(tmp_path, {"years": [2024]}, {"donors-2024.json": ["श्री क", "श्री ख"]})
    a.run(data, review)
    register = json.loads((data / "donors.json").read_text(encoding="utf-8"))
    register["ask"] = bad
    (data / "donors.json").write_text(json.dumps(register, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match='"ask" must be a list of ID pairs'):
        a.run(data, review)


def test_a_spelling_split_by_the_samaj_stops_the_run_where_it_is_printed_again():
    reg, lists = assigned(**{"2024": ["श्री अजय जाट", "श्री अजय जाट एवं श्री ख"]})
    a.apply_answers(reg, answer(a.review_items(reg, lists), False), lists)
    assert reg["pins"] == {"2024#1": {"name": "श्री अजय जाट", "donorIds": ["D0001"]},
                           "2024#2": {"name": "श्री अजय जाट एवं श्री ख", "donorIds": ["D0003", "D0002"]}}
    assert reg["ambiguous"] == ["श्री अजय जाट"]
    a.assign(reg, lists)
    later = lists + lists_of(**{"2026": ["श्री ख", "श्री अजय जाट"]})
    with pytest.raises(ValueError) as exc:
        a.assign(reg, later)
    assert str(exc.value) == (
        "2026#2 uses the spelling 'श्री अजय जाट', which the samaj said belongs to more than "
        "one person. Add a pin for 2026#2 in data/donors.json naming the right ID (D0001, D0003).")
    reg["pins"]["2026#2"] = {"name": "श्री अजय जाट", "donorIds": ["D0003"]}
    a.assign(reg, later)
    assert ids(later, "2026") == [["D0002"], ["D0003"]]
