#!/usr/bin/env python3
"""OBS में live चलाने के पर्दे बनाता है — किनारों की पट्टियाँ और पूरे पर्दे।

    python3 tools/make_obs_kit.py [--base-url http://127.0.0.1:8099] \
        [--only overlay-navratri-07] [--text-out <file>]

दो तरह के चित्र बनते हैं, सब 1920x1080:

  overlay-*  कैमरे के ऊपर चढ़ने वाली पट्टियाँ, पृष्ठभूमि पारदर्शी। हर रात
             का अपना, क्योंकि नीचे की पट्टी पर उस दिन की देवी लिखी है।
  card-*     पूरा पर्दा — प्रारंभ से पहले, बीच के विश्राम में, और अंत में।

देवी और दिन की सूची tools/make_live_thumb.py की NIGHTS से आती है, ताकि
thumbnail और परदे पर एक ही बात लिखी रहे; बदलनी हो तो वहीं बदलिए।
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from make_live_thumb import NIGHTS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "obs"
PLAYWRIGHT = "/home/sverma/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js"

# पूरे पर्दे। slug, ऊपर की पंक्ति, बड़ा लिखा, नीचे की पंक्ति।
CARDS = [
    ("card-pratiksha", "नवदुर्गा महोत्सव 2026",
     "कुछ ही देर में\nप्रारंभ", "महाराणा प्रताप चौराहा, महूनाका इंदौर"),
    ("card-vishram", "नवदुर्गा महोत्सव 2026",
     "थोड़ी देर में\nवापस आते हैं", "बने रहिए"),
    # नीचे की पंक्ति में कल का वादा नहीं: विजयादशमी के बाद अगली रात नहीं
    # होती, और समाज की ओर से कोई बात यहाँ अपने मन से नहीं लिखी जाती।
    ("card-dhanyavaad", "॥ जय माता दी ॥",
     "दर्शन के लिए\nधन्यवाद", "आपका स्नेह बना रहे"),
]

# पदाधिकारी वाला पर्दा पदाधिकारी पन्ने से ही पढ़ा जाता है, अपनी सूची रखकर
# नहीं: समाज जब पन्ने पर पदाधिकारी बदलेगा, पर्दा दोबारा बनाते ही बदल जाएगा।
PADADHIKARI_PAGE = ROOT / "hi" / "padadhikari" / "index.html"
PERSON = re.compile(
    r'<img class="photo" src="(?P<photo>[^"]+)"[^>]*>\s*'
    r'<h3>(?P<name>[^<]+)</h3>\s*'
    r'<p class="role">(?P<role>[^<]+)</p>', re.S)


def officials():
    """पन्ने के "हमारे पदाधिकारी" खंड के पाँच — पूर्व पदाधिकारी इसमें नहीं आते।"""
    page_html = PADADHIKARI_PAGE.read_text(encoding="utf-8")
    start = page_html.index("<h2>हमारे पदाधिकारी</h2>")
    end = page_html.index("<h2>हमारे पूर्व पदाधिकारी</h2>")
    return [{"photo": m["photo"], "name": m["name"],
             # हर पद के आगे "(लोधा समाज इंदौर)" लगा है; पर्दे पर समाज का नाम
             # ऊपर पहले से है, सो यहाँ केवल पद रहता है।
             "role": m["role"].split("(")[0].strip()}
            for m in PERSON.finditer(page_html[start:end])]


OVERLAY = """
  <figure class="screen overlay" id="overlay-{slug}">
    <div class="bug">
      <img src="/assets/img/logo-social.png" alt="">
      <b>लोधा समाज इंदौर</b>
      <span class="live"><i></i>LIVE</span>
    </div>
    <div class="third">
      <div class="bar"></div>
      <div class="body">
        <p class="kicker">{kicker}</p>
        <h2>{line}</h2>
      </div>
    </div>
    <div class="addr">lodhasamaj.org</div>
  </figure>
"""

CARD = """
  <figure class="screen card" id="{slug}">
    <img class="bg" src="/assets/img/gallery/2026/pratima-7.jpg" alt="">
    <div class="veil"></div>
    <div class="plate">
      <div>
        <img class="logo" src="/assets/img/logo-social.png" alt="">
        <p class="kicker">{kicker}</p>
        <h2>{head}</h2>
        <p class="sub">{sub}</p>
        <p class="url">lodhasamaj.org</p>
      </div>
    </div>
    <div class="strip"></div>
  </figure>
"""

# भंडारे का पूरा पर्दा। दिन और समय समाज के अपने निमंत्रण पत्र से हैं, जो
# दायीं ओर पूरा का पूरा दिखता भी है - छपे हुए पत्र को काटा नहीं जाता।
BHANDARA = {
    "kicker": "23वाँ आयोजन · लोधा समाज उत्सव समिति (सन् 1981)",
    "title": "नगर कन्या भोज<br>एवं विशाल भंडारा",
    "day": "शुक्रवार, 23 अक्टूबर 2026",
    "times": [("महाआरती", "शाम 7 बजे"), ("महाप्रसादी", "शाम 7:30 बजे")],
    "where": "लोधा कॉलोनी, महूनाका चौराहा, इंदौर",
    "nimantran": "/assets/img/karyakram/bhandara-2026-nimantran.jpg",
}

BHANDARA_CARD = """
  <figure class="screen card nyota" id="{slug}">
    <img class="bg" src="/assets/img/gallery/2026/pratima-7.jpg" alt="">
    <div class="veil"></div>
    <div class="side">
      <p class="kicker">{kicker}</p>
      <h2>{title}</h2>
      <p class="day">{day}</p>
      <ul class="times">{times}</ul>
      <p class="where">{where}</p>
      <div class="foot">
        <img src="/assets/img/logo-social.png" alt="">
        <div>
          <p class="url">lodhasamaj.org</p>
          <p class="who">लोधा समाज इंदौर</p>
        </div>
      </div>
    </div>
    <div class="patra"><img src="{nimantran}" alt=""></div>
    <div class="strip"></div>
  </figure>
"""

TIME_ROW = """
        <li><b>{0}</b><span>{1}</span></li>"""

PEOPLE = """
  <figure class="screen card people" id="{slug}">
    <img class="bg" src="/assets/img/gallery/2026/pratima-7.jpg" alt="">
    <div class="veil"></div>
    <div class="sheet">
      <p class="kicker">नवदुर्गा महोत्सव 2026 · लोधा समाज इंदौर</p>
      <h2>हमारे पदाधिकारी</h2>
      <ul class="row">{people}</ul>
      <p class="url">lodhasamaj.org</p>
    </div>
    <div class="strip"></div>
  </figure>
"""

PERSON_CELL = """
        <li>
          <img src="{photo}" alt="">
          <b>{name}</b>
          <span>{role}</span>
        </li>"""

CAPTURE = r"""
import pw from '%(playwright)s';
const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
const p = await b.newPage({ viewport: { width: 2000, height: 1200 }, deviceScaleFactor: 1 });
await p.goto('%(url)s', { waitUntil: 'networkidle' });
await p.waitForTimeout(1500);
for (const [slug, transparent] of %(shots)s) {
  await p.locator('#' + slug).screenshot({ path: '%(out)s/' + slug + '-1920x1080.png',
                                           omitBackground: transparent });
  console.log(slug);
}
await b.close();
"""


def overlay_slug(night) -> str:
    return "overlay-" + night["slug"]


def third_line(night) -> str:
    """नीचे की पट्टी की पंक्ति। दिन का नाम तभी जोड़ा जाता है जब वह देवी के
    नाम में पहले से न हो - "दशमी · विजयादशमी महोत्सव" दो बार एक ही बात है।"""
    title = night["title"].replace("\n", " ")
    return title if night["day"] in title else f'{night["day"]} · {title}'


def filename(slug, transparent) -> str:
    """overlay को पारदर्शिता चाहिए, सो PNG; पूरे पर्दे छायाचित्र हैं, सो JPEG -
    वही कारण जो youtube kit में thumbnail के लिए है।"""
    return f"{slug}-1920x1080." + ("png" if transparent else "jpg")


def screens():
    """हर पर्दा एक बार: (slug, html, पारदर्शी?)।"""
    out = []
    for night in NIGHTS:
        out.append((overlay_slug(night), OVERLAY.format(
            slug=night["slug"], kicker=night["kicker"],
            line=third_line(night)), True))
    for slug, kicker, head, sub in CARDS:
        out.append((slug, CARD.format(slug=slug, kicker=kicker,
                                      head=head.replace("\n", "<br>"), sub=sub), False))
    cells = "".join(PERSON_CELL.format(**person) for person in officials())
    out.append(("card-padadhikari", PEOPLE.format(slug="card-padadhikari",
                                                  people=cells), False))
    rows = "".join(TIME_ROW.format(*pair) for pair in BHANDARA["times"])
    out.append(("card-bhandara", BHANDARA_CARD.format(slug="card-bhandara",
                                                      times=rows, **{
        k: v for k, v in BHANDARA.items() if k != "times"}), False))
    return out


def page(chosen) -> str:
    template = (ROOT / "tools" / "obs-kit.html.in").read_text(encoding="utf-8")
    return template.replace("<!-- CARDS -->", "".join(html for _, html, _ in chosen))


def text_kit(chosen) -> str:
    lines = "\n".join(f"       {filename(slug, t)}" for slug, _, t in chosen)
    return f"""लोधा समाज इंदौर — OBS के पर्दे
चित्र: assets/img/obs/   (सब 1920x1080)

{lines}

OBS में कैसे लगाएँ
══════════════════════════════════════════════════════════

एक बार का काम

1. Settings → Video में दोनों Resolution 1920x1080 रखिए।
   परदे इसी नाप के हैं; नाप अलग हुई तो पट्टियाँ खिसकी दिखेंगी।

2. Scenes में चार दृश्य बनाइए:
       प्रतीक्षा     — प्रारंभ से पहले
       मंच          — असली live
       विश्राम       — बीच में
       धन्यवाद      — अंत में

3. "मंच" दृश्य में दो Source रखिए, इसी क्रम में (ऊपर वाला ऊपर दिखता है):
       Image  →  overlay-navratri-07-1920x1080.png   ← ऊपर
       Video Capture / कैमरा                          ← नीचे
   overlay की पृष्ठभूमि पारदर्शी है, सो कैमरा उसमें से दिखता रहेगा।
   बीच का हिस्सा खाली रखा गया है — माँ की प्रतिमा कभी नहीं ढँकेगी।

4. बाक़ी तीन दृश्यों में एक-एक Image डालिए:
       प्रतीक्षा  →  card-pratiksha-1920x1080.jpg
       विश्राम   →  card-vishram-1920x1080.jpg
       धन्यवाद  →  card-dhanyavaad-1920x1080.jpg

   भंडारे वाला पर्दा — card-bhandara-1920x1080.jpg — 23 अक्टूबर के live
   में प्रारंभ से पहले और बीच-बीच में दिखाइए। उस पर दिन, महाआरती और
   महाप्रसादी का समय, स्थान, और समाज का निमंत्रण पत्र पूरा है।

   पदाधिकारी वाला पर्दा — card-padadhikari-1920x1080.jpg — किसी भी दृश्य
   में डालकर बीच-बीच में दिखाया जा सकता है, या उसका अपना एक दृश्य बना
   लीजिए। उस पर पाँचों पदाधिकारी नाम और पद सहित हैं।

हर रात का काम

5. "मंच" दृश्य में overlay वाली Image पर दो बार दबाकर उस रात की फ़ाइल
   चुन लीजिए — सातवें दिन overlay-navratri-07, आठवें दिन -08, इसी तरह।
   और कुछ बदलने की ज़रूरत नहीं।

6. live का thumbnail, शीर्षक और विवरण अलग kit में हैं:
       python3 tools/make_live_thumb.py

══════════════════════════════════════════════════════════
दोबारा बनाने के लिए: python3 tools/make_obs_kit.py
लिखा हुआ बदलना हो तो make_live_thumb.py की NIGHTS सूची, और पूरे परदों
के लिए make_obs_kit.py की CARDS सूची।
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8099",
                    help="a server with the repo at its root, for the screenshots")
    ap.add_argument("--only", action="append", help="केवल ये slug बनाइए")
    ap.add_argument("--text-out", type=Path, help="शब्द इस फ़ाइल में भी लिखिए")
    args = ap.parse_args(argv)

    chosen = [s for s in screens() if not args.only or s[0] in args.only]
    if not chosen:
        print("कोई पर्दा नहीं मिला; slug देखिए", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    tmp = ROOT / ".obs-kit.html"
    tmp.write_text(page(chosen), encoding="utf-8")
    try:
        shots = [[slug, transparent] for slug, _, transparent in chosen]
        script = CAPTURE % {"playwright": PLAYWRIGHT, "out": str(OUT),
                            "url": args.base_url.rstrip("/") + "/.obs-kit.html",
                            "shots": repr(shots).replace("'", '"')
                                                .replace("True", "true")
                                                .replace("False", "false")}
        subprocess.run(["node", "--input-type=module", "-e", script], check=True)
    finally:
        tmp.unlink(missing_ok=True)

    # overlay PNG ही रहते हैं - उनकी पारदर्शिता ही उनका काम है। पूरे पर्दे
    # छायाचित्र हैं, वे JPEG में कहीं सस्ते पड़ते हैं।
    for slug, _, transparent in chosen:
        made = OUT / f"{slug}-1920x1080.png"
        final = OUT / filename(slug, transparent)
        if transparent:
            subprocess.run(["mogrify", "-strip", str(final)], check=True)
        else:
            subprocess.run(["convert", str(made), "-strip", "-interlace", "Plane",
                            "-quality", "90", str(final)], check=True)
            made.unlink()
        px = subprocess.run(["identify", "-format", "%wx%h", str(final)],
                            capture_output=True, text=True, check=True).stdout
        print(f"  {final.relative_to(ROOT)}  {px}  {final.stat().st_size // 1024} KB")

    kit = text_kit(chosen)
    if args.text_out:
        args.text_out.write_text(kit, encoding="utf-8")
        print(f"\nशब्द {args.text_out} में लिखे गए")
    else:
        print("\n" + kit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
