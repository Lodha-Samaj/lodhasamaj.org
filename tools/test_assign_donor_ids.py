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
