"""OBS के परदे जाँचता है।

खींचे हुए चित्र repo में हैं, सो दो तरह की जाँच यहाँ होती है: पर्दे की
बनावट (बिना browser के), और बनी हुई PNG पर यह कि overlay सचमुच पारदर्शी
है और उसका बीच खाली है - वही इन परदों की पूरी शर्त है।
"""
import shutil
import subprocess

import pytest

from make_live_thumb import NIGHTS
from make_obs_kit import (BHANDARA, CARDS, OUT, PADADHIKARI_PAGE, filename,
                          officials, overlay_slug, page, screens, text_kit,
                          third_line)

ALL = screens()
IDS = [s[0] for s in ALL]
OVERLAYS = [s[0] for s in ALL if s[2]]


def pixel(path, x, y):
    out = subprocess.run(["convert", str(path), "-format", f"%[pixel:p{{{x},{y}}}]",
                          "info:"], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def test_har_raat_ka_overlay_hai_aur_naam_dohraya_nahi():
    assert len(set(IDS)) == len(IDS)
    for night in NIGHTS:
        assert overlay_slug(night) in IDS, night["slug"]
    # हर रात का overlay, CARDS के पर्दे, और दो अपने — पदाधिकारी तथा भंडारा।
    assert len(ALL) == len(NIGHTS) + len(CARDS) + 2
    assert "card-padadhikari" in IDS and "card-bhandara" in IDS


def test_overlay_pardarshi_hai_aur_poore_parde_nahi():
    for slug, _, transparent in ALL:
        assert transparent == slug.startswith("overlay-"), slug


@pytest.mark.parametrize("night", NIGHTS, ids=[n["slug"] for n in NIGHTS])
def test_overlay_par_us_raat_ki_devi_aur_din_likha_hai(night):
    html = next(h for slug, h, _ in ALL if slug == overlay_slug(night))
    assert third_line(night) in html
    assert night["title"].replace("\n", " ") in html
    assert night["kicker"] in html
    assert "lodhasamaj.org" in html and "LIVE" in html


def test_overlay_me_koi_poora_dhakne_wali_cheez_nahi():
    # overlay पर केवल तीन तख़्तियाँ हैं, तीनों किनारे से बँधी; कोई चौथी
    # चीज़ जुड़ी तो वह बीच में पड़ सकती है, इसलिए गिनती बँधी हुई है।
    for slug, html, transparent in ALL:
        if not transparent:
            continue
        assert html.count("<div") == 5, slug  # bug, third, bar, body, addr
        assert 'class="bg"' not in html and "veil" not in html


def test_parde_ke_kone_css_me_bandhe_hain():
    css = (OUT.parent.parent.parent / "tools" / "obs-kit.html.in").read_text(encoding="utf-8")
    assert ".overlay { background: transparent; }" in css
    for anchor in (".bug { position: absolute; top: 42px; left: 48px;",
                   ".third { position: absolute; left: 48px; bottom: 56px;",
                   ".addr { position: absolute; right: 48px; bottom: 56px;"):
        assert anchor in css, anchor


def test_poore_parde_do_panktiyon_me_likhe_hain():
    for slug, _, head, _ in CARDS:
        assert head.count("\n") == 1, slug
        assert all(line.strip() for line in head.split("\n")), slug


def test_panne_me_har_parda_ek_baar_aata_hai():
    html = page(ALL)
    assert "<!-- CARDS -->" not in html
    for slug in IDS:
        assert html.count(f'id="{slug}"') == 1
    assert html.count('class="screen') == len(ALL)


def test_shabdon_me_har_file_aur_obs_ke_kadam_hain():
    kit = text_kit(ALL)
    for slug, _, transparent in ALL:
        assert filename(slug, transparent) in kit
    assert "1920x1080" in kit and "Scenes" in kit
    # कैमरा overlay के नीचे रहे, यही सबसे आसानी से उलटा लगाया जाता है।
    assert kit.index("overlay-navratri-07-1920x1080.png") < kit.index("Video Capture")


@pytest.mark.parametrize("slug", OVERLAYS)
def test_bani_hui_overlay_ka_beech_khali_hai(slug):
    path = OUT / filename(slug, True)
    if not path.exists():
        pytest.skip(f"{path.name} अभी बना नहीं — python3 tools/make_obs_kit.py")
    if not shutil.which("convert"):
        pytest.skip("ImageMagick नहीं मिला")
    # बीच की तिहाई में कहीं भी रंग नहीं होना चाहिए: प्रतिमा वहीं रहती है।
    for x, y in ((960, 540), (700, 400), (1200, 700), (960, 180), (960, 880)):
        assert pixel(path, x, y).endswith(",0)"), f"{slug} पर ({x},{y}) ढँका है"
    # और पट्टियाँ सचमुच बनी हैं: नीचे-बायाँ कोना भरा हुआ मिले।
    assert not pixel(path, 120, 980).endswith(",0)"), f"{slug} की नीचे वाली पट्टी ग़ायब है"


def test_overlay_png_rehte_hain_aur_poore_parde_jpeg():
    # पारदर्शिता केवल PNG रखता है; JPEG में overlay की काली तख़्ती पूरा
    # कैमरा ढँक देगी, इसलिए यह अदला-बदली पकड़ी जानी चाहिए।
    assert filename("overlay-navratri-07", True).endswith(".png")
    assert filename("card-vishram", False).endswith(".jpg")


def test_din_ka_naam_dohraya_nahi_jata():
    # नवरात्रि की रातों पर दिन और देवी दोनों लिखे जाते हैं।
    for night in NIGHTS:
        if night["slug"] != "vijayadashami":
            assert third_line(night).startswith(night["day"] + " · "), night["slug"]
    # विजयादशमी पर "दशमी" नाम में ही है, सो आगे दोबारा नहीं आता।
    dashami = next(n for n in NIGHTS if n["slug"] == "vijayadashami")
    assert third_line(dashami) == "विजयादशमी महोत्सव"


def test_padadhikari_wale_parde_par_paanchon_hain():
    people = officials()
    assert len(people) == 5, "समाज के 2026 के पदाधिकारी पाँच हैं"
    html = next(h for slug, h, _ in ALL if slug == "card-padadhikari")
    for person in people:
        assert person["name"] in html
        assert person["role"] in html
        assert person["photo"] in html
        assert (OUT.parent.parent.parent / person["photo"].lstrip("/")).exists()


def test_poorv_padadhikari_is_parde_par_nahi_aate():
    # खंड की सीमा सही बँधी है या नहीं, यह इसी से पकड़ा जाता है: पन्ने पर
    # पूर्व पदाधिकारी ठीक इसके नीचे हैं।
    names = [p["name"] for p in officials()]
    page_html = PADADHIKARI_PAGE.read_text(encoding="utf-8")
    after = page_html[page_html.index("<h2>हमारे पूर्व पदाधिकारी</h2>"):]
    for name in names:
        assert name not in after, f"{name} पूर्व पदाधिकारी में भी है"
    assert "ब्रह्मलीन" not in " ".join(names)


def test_pad_ke_aage_samaj_ka_naam_dobara_nahi():
    # पन्ने पर हर पद के आगे "(लोधा समाज इंदौर)" लगा है; पर्दे पर समाज का
    # नाम ऊपर पहले से है।
    for person in officials():
        assert "(" not in person["role"], person["name"]


def test_padadhikari_parda_jpeg_hai_aur_kit_me_likha_hai():
    assert ("card-padadhikari", False) in [(s[0], s[2]) for s in ALL]
    kit = text_kit(ALL)
    assert "card-padadhikari-1920x1080.jpg" in kit
    assert "पदाधिकारी" in kit


def test_bhandare_ke_parde_par_patra_samay_aur_sthan_hain():
    html = next(h for slug, h, _ in ALL if slug == "card-bhandara")
    assert BHANDARA["nimantran"] in html
    assert (OUT.parent.parent.parent / BHANDARA["nimantran"].lstrip("/")).exists()
    assert BHANDARA["day"] in html and BHANDARA["where"] in html
    for name, when in BHANDARA["times"]:
        assert name in html and when in html
    assert ("card-bhandara", False) in [(s[0], s[2]) for s in ALL]
    assert "card-bhandara-1920x1080.jpg" in text_kit(ALL)


def test_bhandare_ka_sthan_patra_wala_hi_rahe():
    # निमंत्रण पत्र और बैनर दोनों लोधा कॉलोनी कहते हैं; बाक़ी आयोजनों का
    # महाराणा प्रताप चौराहा यहाँ नहीं आना चाहिए।
    html = next(h for slug, h, _ in ALL if slug == "card-bhandara")
    assert "लोधा कॉलोनी" in BHANDARA["where"]
    assert "महाराणा प्रताप" not in html
