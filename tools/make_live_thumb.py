#!/usr/bin/env python3
"""नवदुर्गा महोत्सव की रातों के YouTube live के thumbnail बनाता है।

    python3 tools/make_live_thumb.py [--base-url http://127.0.0.1:8099] \
        [--only navratri-07] [--text-out <file>]

हर रात का अपना कार्ड है: उस दिन की देवी, दिन का अंक, और समाज की अपनी
2026 की प्रतिमा का एक चित्र। कार्ड ठीक 1280x720 पर बनता है और उसी नाप पर
screenshot होता है, क्योंकि बाद में नाप बदलने पर अक्षर धुँधले पड़ते हैं।

देवी के नाम और स्वरूप पंचांग के हैं, समाज के नहीं। तिथि किस दिन पड़ेगी यह
पंचांग के अनुसार बदल सकती है - दिन का मिलान समाज से कर लेना चाहिए, और
बदलना हो तो नीचे NIGHTS में एक पंक्ति बदलनी है, और कहीं नहीं।
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "youtube"
PLAYWRIGHT = "/home/sverma/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js"

# हर रात का कार्ड। title में \n जहाँ है, वहीं नाम की पंक्ति टूटती है -
# 104px पर एक पंक्ति में लगभग दस अक्षर ही पट्टी में समाते हैं।
NIGHTS = [
    {"slug": "navratri-07", "num": "७", "kicker": "नवदुर्गा महोत्सव 2026",
     "title": "माँ\nकालरात्रि", "day": "सातवाँ दिन", "photo": "pratima-6.jpg",
     "bhog": "गुड़"},
    {"slug": "navratri-08", "num": "८", "kicker": "नवदुर्गा महोत्सव 2026",
     "title": "माँ\nमहागौरी", "day": "आठवाँ दिन", "photo": "pratima-4.jpg",
     "bhog": "नारियल"},
    {"slug": "navratri-09", "num": "९", "kicker": "नवदुर्गा महोत्सव 2026",
     "title": "माँ\nसिद्धिदात्री", "day": "नवाँ दिन", "photo": "pratima-5.jpg",
     "bhog": "हलवा-पूरी"},
    {"slug": "vijayadashami", "num": "१०", "kicker": "लोधा समाज इंदौर · महूनाका",
     "title": "विजयादशमी\nमहोत्सव", "day": "दशमी", "photo": "pratima-7.jpg",
     "bhog": ""},
    # नवरात्रि की रात नहीं, पर उसी महीने का आयोजन और उसी kit से बनता है।
    # समय शाम का है, रात्रि का नहीं, और नाम लंबा है - सो time और size।
    #
    # गिनती: समाज के निमंत्रण पत्र पर "23 वाँ नगर कन्या भोज एवं विशाल
    # भण्डारा" छपा है, और events.json तथा समाज की सूचना भी कन्या पूजन को
    # 23वाँ कहती है - सो कार्ड पर 23 ही जाता है। भंडारे की अपनी गिनती समाज
    # ने 2026-10-23 की सूचना में 47वाँ बताई (पहले की सूचना 46वाँ कहती थी),
    # और वही data/donors-2026.json तथा events.json में है; कार्ड पर कन्या
    # भोज की गिनती छपती है, भंडारे की नहीं।
    {"slug": "bhandara", "num": "२३", "kicker": "23वाँ आयोजन · लोधा समाज इंदौर",
     "title": "नगर कन्या भोज\nएवं विशाल भंडारा", "day": "शुक्रवार, 23 अक्टूबर",
     "time": "शाम ७ बजे से", "size": 64, "photo": "pratima-3.jpg", "bhog": ""},
]

CARD = """
  <figure class="thumb" id="{slug}">
    <div class="panel">
      <span class="num">{num}</span>
      <span class="live"><i></i>LIVE</span>
      <p class="kicker">{kicker}</p>
      <h2 style="font-size:{size}px">{title}</h2>
      <div class="rule"></div>
      <p class="day">{day} · {time}</p>
      <div class="bottom">
        <img src="/assets/img/logo-social.png" alt="">
        <div>
          <p class="url">lodhasamaj.org</p>
          <p class="foot">लोधा समाज इंदौर</p>
        </div>
      </div>
    </div>
    <div class="shot">
      <img src="/assets/img/gallery/2026/{photo}" alt="">
      <div class="edge"></div>
    </div>
  </figure>
"""

CAPTURE = r"""
import pw from '%(playwright)s';
const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
// deviceScaleFactor 1, कार्ड पूरी नाप पर बना हुआ: जो खिंचता है वही नाप है।
const p = await b.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
await p.goto('%(url)s', { waitUntil: 'networkidle' });
await p.waitForTimeout(1500);
for (const slug of %(slugs)s) {
  await p.locator('#' + slug).screenshot({ path: '%(out)s/thumb-' + slug + '-1280x720.png' });
  console.log(slug);
}
await b.close();
"""


def card(night) -> str:
    return CARD.format(photo=night["photo"], num=night["num"],
                       kicker=night["kicker"], slug=night["slug"],
                       title=night["title"].replace("\n", "<br>"),
                       day=night["day"], time=night.get("time", "रात्रि ८ बजे"),
                       size=night.get("size", 104))


def page(nights) -> str:
    template = (ROOT / "tools" / "live-thumb.html.in").read_text(encoding="utf-8")
    return template.replace("<!-- CARDS -->", "".join(card(n) for n in nights))


def words(night) -> str:
    slug, title, day = night["slug"], night["title"].replace("\n", " "), night["day"]
    if slug == "bhandara":
        return f"""
   ── नगर कन्या भोज एवं विशाल भंडारा ─────────────────────
   thumbnail: thumb-bhandara-1280x720.jpg
   शीर्षक  : LIVE | 23वाँ नगर कन्या भोज एवं विशाल भंडारा | लोधा समाज इंदौर
   विवरण   :
नगर कन्या भोज एवं विशाल भंडारा का सीधा प्रसारण —
शुक्रवार, 23 अक्टूबर 2026।

महाआरती: शाम 7 बजे
महाप्रसादी: शाम 7:30 बजे
स्थान: लोधा कॉलोनी, महूनाका चौराहा, इंदौर

आयोजक: लोधा समाज उत्सव समिति (सन् 1981) · लोधा समाज इंदौर
वेबसाइट: https://lodhasamaj.org
संपर्क: +91 90987 81740
॥ जय माता दी ॥
   tags    : विशाल भंडारा, नगर कन्या भोज, कन्या पूजन, महाप्रसादी,
             लोधा समाज इंदौर, महूनाका, इंदौर, Bhandara, Kanya Bhoj, Indore
"""
    if slug == "vijayadashami":
        return f"""
   ── विजयादशमी ─────────────────────────────────────────
   thumbnail: thumb-vijayadashami-1280x720.jpg
   शीर्षक  : LIVE | विजयादशमी महोत्सव 2026 | लोधा समाज इंदौर
   विवरण   :
विजयादशमी महोत्सव 2026 का सीधा प्रसारण — महाराणा प्रताप चौराहा,
महूनाका इंदौर, रात्रि 8 बजे।

आयोजक: लोधा समाज इंदौर · https://lodhasamaj.org
संपर्क: +91 90987 81740
॥ जय माता दी ॥
   tags    : विजयादशमी, दशहरा 2026, नवदुर्गा महोत्सव, लोधा समाज इंदौर,
             महूनाका, Vijayadashami, Dussehra 2026, Indore
"""
    return f"""
   ── {day} — {title} ──────────────────────────────
   thumbnail: thumb-{slug}-1280x720.jpg
   शीर्षक  : LIVE | नवदुर्गा महोत्सव 2026 — {day}, {title} | लोधा समाज इंदौर
   विवरण   :
नवदुर्गा महोत्सव 2026 का {day} — {title} की आराधना।
सीधा प्रसारण: महाराणा प्रताप चौराहा, महूनाका इंदौर, रात्रि 8 बजे।

इस दिन भोग में {night["bhog"]} अर्पित किया जाता है।

आयोजक: लोधा समाज इंदौर · https://lodhasamaj.org
संपर्क: +91 90987 81740
॥ जय माता दी ॥
   tags    : नवदुर्गा महोत्सव, नवरात्रि 2026, {title}, {day}, गरबा,
             लोधा समाज इंदौर, महूनाका, Navratri 2026, Indore
"""


def text_kit(nights) -> str:
    head = """लोधा समाज इंदौर — नवदुर्गा महोत्सव 2026, live के thumbnail और शब्द
चैनल: https://www.youtube.com/@LodhaSamajIndoreOfficial

चित्र assets/img/youtube/ में हैं, हर एक 1280x720। live शुरू करते समय
YouTube में "Custom thumbnail" पर यही चढ़ाइए, और नीचे के शीर्षक एवं
विवरण लगाइए।
══════════════════════════════════════════════════════════
"""
    return head + "".join(words(n) for n in nights) + """
══════════════════════════════════════════════════════════
दोबारा बनाने के लिए: python3 tools/make_live_thumb.py
दिन या देवी बदलनी हो तो tools/make_live_thumb.py की NIGHTS सूची बदलिए।
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8099",
                    help="a server with the repo at its root, for the screenshots")
    ap.add_argument("--only", action="append", help="केवल ये slug बनाइए")
    ap.add_argument("--text-out", type=Path, help="शब्द इस फ़ाइल में भी लिखिए")
    args = ap.parse_args(argv)

    nights = [n for n in NIGHTS if not args.only or n["slug"] in args.only]
    if not nights:
        print("कोई रात नहीं मिली; slug देखिए", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    tmp = ROOT / ".live-thumb.html"
    tmp.write_text(page(nights), encoding="utf-8")
    try:
        script = CAPTURE % {"playwright": PLAYWRIGHT, "out": str(OUT),
                            "url": args.base_url.rstrip("/") + "/.live-thumb.html",
                            "slugs": repr([n["slug"] for n in nights]).replace("'", '"')}
        subprocess.run(["node", "--input-type=module", "-e", script], check=True)
    finally:
        tmp.unlink(missing_ok=True)

    # thumbnail JPEG में जाते हैं: YouTube इन्हें 2 MB तक रखता है, और अक्षरों
    # के नीचे का छायाचित्र JPEG में कहीं सस्ता पड़ता है।
    for slug in (n["slug"] for n in nights):
        made = OUT / f"thumb-{slug}-1280x720.png"
        final = OUT / f"thumb-{slug}-1280x720.jpg"
        subprocess.run(["convert", str(made), "-strip", "-interlace", "Plane",
                        "-quality", "90", str(final)], check=True)
        made.unlink()
        px = subprocess.run(["identify", "-format", "%wx%h", str(final)],
                            capture_output=True, text=True, check=True).stdout
        print(f"  {final.relative_to(ROOT)}  {px}  {final.stat().st_size // 1024} KB")

    kit = text_kit(nights)
    if args.text_out:
        args.text_out.write_text(kit, encoding="utf-8")
        print(f"\nशब्द {args.text_out} में लिखे गए")
    else:
        print("\n" + kit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
