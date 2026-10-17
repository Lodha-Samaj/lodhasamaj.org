"""live thumbnail के कार्ड जाँचता है - चित्र खींचे बिना।

screenshot के लिए browser चाहिए, सो वह यहाँ नहीं होता; जो यहाँ होता है वह
इतना है कि साँचे में कार्ड सही बैठें और जिन चित्रों का नाम लिखा है वे सचमुच
फ़ोल्डर में हों।
"""
import re

import pytest

from make_live_thumb import NIGHTS, ROOT, card, page, text_kit

IDS = [n["slug"] for n in NIGHTS]


def test_har_raat_ka_chitra_repo_me_maujood_hai():
    for night in NIGHTS:
        path = ROOT / "assets" / "img" / "gallery" / "2026" / night["photo"]
        assert path.exists(), f"{night['slug']} का चित्र नहीं मिला: {path}"


def test_slug_aur_ank_dohraye_nahi_gaye():
    assert len(set(IDS)) == len(IDS)
    nums = [n["num"] for n in NIGHTS]
    assert len(set(nums)) == len(nums)


@pytest.mark.parametrize("night", NIGHTS, ids=IDS)
def test_kard_par_devi_din_aur_pata_likha_hai(night):
    html = card(night)
    assert f'id="{night["slug"]}"' in html
    assert f">{night['num']}</span>" in html
    assert night["day"] in html and night["photo"] in html
    assert night["kicker"] in html
    assert "lodhasamaj.org" in html
    assert "LIVE" in html
    # नाम टूटा नहीं: <br> हटाने पर वही नाम वापस मिले।
    assert html.count("<h2>") == 1
    head = re.search(r"<h2>(.+?)</h2>", html, re.S).group(1)
    assert head.replace("<br>", "\n") == night["title"]


@pytest.mark.parametrize("night", NIGHTS, ids=IDS)
def test_naam_do_panktiyon_me_tutata_hai(night):
    # 104px पर पूरा नाम एक पंक्ति में पट्टी से बाहर निकल जाता है, सो हर नाम
    # दो पंक्तियों में बँटा है। पंक्ति कितनी चौड़ी पड़ेगी यह अक्षर गिनकर नहीं
    # जाना जा सकता - देवनागरी की मात्राएँ अलग से चौड़ाई नहीं लेतीं - वह
    # बने हुए चित्र को देखकर ही जाँचा जाता है।
    lines = night["title"].split("\n")
    assert len(lines) == 2, night["slug"]
    assert all(line.strip() for line in lines), night["slug"]


def test_panne_me_har_raat_ek_baar_aati_hai():
    html = page(NIGHTS)
    assert "<!-- CARDS -->" not in html, "साँचे का निशान बदला नहीं गया"
    for slug in IDS:
        assert html.count(f'id="{slug}"') == 1
    assert html.count('class="thumb"') == len(NIGHTS)


def test_sirf_chuni_hui_raat_banti_hai():
    html = page([NIGHTS[0]])
    assert html.count('class="thumb"') == 1
    assert f'id="{IDS[1]}"' not in html


@pytest.mark.parametrize("night", NIGHTS, ids=IDS)
def test_shabdon_me_sheershak_vivaran_aur_thumbnail_ka_naam_hai(night):
    kit = text_kit([night])
    assert f"thumb-{night['slug']}-1280x720.jpg" in kit
    assert night["title"].replace("\n", " ") in kit
    assert "https://lodhasamaj.org" in kit
    assert "+91 90987 81740" in kit
    # भोग केवल वहीं छपे जहाँ लिखा है; विजयादशमी पर भोग की पंक्ति नहीं आती।
    assert ("भोग में" in kit) == bool(night["bhog"])
    if night["bhog"]:
        assert f"भोग में {night['bhog']} अर्पित" in kit


def test_vijayadashami_ko_navdurga_mahotsav_nahi_kaha_gaya():
    # events.json में ये दो अलग आयोजन हैं; कार्ड पर भी अलग ही रहें।
    dashami = next(n for n in NIGHTS if n["slug"] == "vijayadashami")
    assert "नवदुर्गा" not in card(dashami)
    for night in NIGHTS:
        if night["slug"] != "vijayadashami":
            assert night["kicker"] == "नवदुर्गा महोत्सव 2026"
