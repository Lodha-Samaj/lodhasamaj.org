#!/usr/bin/env python3
"""Builds the kit for the समाज's YouTube channel: five pictures and the words.

    python3 tools/make_youtube_kit.py [--base-url http://127.0.0.1:8099] \
        [--text-out <file>]

The channel already exists - @LodhaSamajIndoreOfficial, 307 subscribers and 47
videos as of 17 October 2026 - so this is a kit for finishing it, not for
starting one. What it is missing is a link to the website, a description longer
than one line, and artwork carrying the address. That is what this makes.

Each picture is drawn at exactly the size YouTube asks for and screenshot at
that size, so nothing is resized afterwards - resizing is where text goes soft,
and these are mostly text.

The words are printed, not pasted anywhere by this script: filling in a channel
needs someone signed in to that channel, and that is not this machine.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img" / "youtube"
PLAYWRIGHT = "/home/sverma/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js"
CHANNEL = "https://www.youtube.com/@LodhaSamajIndoreOfficial"

# id in the template -> (file name, what YouTube calls it, transparent?)
SHOTS = [
    ("banner",         "banner-2560x1440.png",   "channel banner", False),
    ("avatar",         "avatar-800x800.png",     "profile picture", False),
    ("thumb-parichay", "thumb-parichay-1280x720.jpg", "thumbnail: the introduction reel", False),
    ("thumb-garba",    "thumb-garba-1280x720.jpg",    "thumbnail: the garba reel", False),
    ("watermark",      "watermark-150x150.png",  "video watermark", True),
]

CAPTURE = r"""
import pw from '%(playwright)s';
const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
// deviceScaleFactor 1 with the cards authored at full size: what is shot is
// already the exact pixel size YouTube wants.
const p = await b.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 1 });
await p.goto('%(url)s', { waitUntil: 'networkidle' });
await p.waitForTimeout(1200);
for (const [id, file, transparent] of %(shots)s) {
  await p.locator('#' + id).screenshot({ path: '%(out)s/' + file, omitBackground: transparent });
  console.log(id, '->', file);
}
await b.close();
"""


def text_kit() -> str:
    return f"""लोधा समाज इंदौर — YouTube चैनल kit
चैनल: {CHANNEL}

जो बदलना है, क्रम से
══════════════════════════════════════════════════════════

1. LINKS में वेबसाइट जोड़िए  (सबसे ज़रूरी)
   अभी केवल Instagram लगा है। YouTube Studio → Customisation →
   Basic info → Links में ये जोड़िए:

       Website     https://lodhasamaj.org
       Facebook    https://www.facebook.com/profile.php?id=61552495104262
       Instagram   https://www.instagram.com/lodha.samaj/
       WhatsApp    https://wa.me/919098781740

   पहली कड़ी बैनर पर भी दिखती है, सो वेबसाइट को पहले रखिए।

2. DESCRIPTION — अभी एक पंक्ति है। यह लगाइए:
   (YouTube Studio → Customisation → Basic info → Description)

   ──────────────────────────────────────────────────────
लोधा समाज इंदौर का आधिकारिक YouTube चैनल।

यहाँ समाज के आयोजनों के वीडियो रहते हैं — नवदुर्गा महोत्सव और गरबा,
नगर कन्या भोज एवं विशाल भंडारा, श्री नर्मदेश्वर महादेव कावड़ यात्रा,
और समाज के अन्य कार्यक्रम।

समाज की वेबसाइट: https://lodhasamaj.org
वहाँ आयोजनों की तिथियाँ, तीनों आयोजनों की वर्षवार दानदाता सूचियाँ
(नाम और मात्रा सहित), छात्रवृत्तियों और सरकारी स्वास्थ्य सेवाओं की
जानकारी, पदाधिकारियों का परिचय और समाज का संपर्क — सब एक जगह है।

आयोजन स्थल: लोधा कॉलोनी धर्मशाला, महाराणा प्रताप चौराहा,
महूनाका इंदौर, मध्यप्रदेश
संपर्क: +91 90987 81740 · lodhasamajindore@gmail.com

॥ जय माता दी ॥
   ──────────────────────────────────────────────────────

3. चित्र बदलिए  (Customisation → Branding)
   बैनर, प्रोफ़ाइल चित्र और watermark — तीनों इस kit में हैं, सही नाप में।
   बैनर पर वेबसाइट का पता लिखा है, यही उसका काम है।

4. वीडियो चढ़ाइए
   वेबसाइट पर दो वीडियो तैयार हैं, दोनों के thumbnail भी इस kit में हैं:

   ── परिचय रील ──────────────────────────────────────────
   फ़ाइल   : assets/video/2026/parichay-reel.mp4  (90 सेकंड)
   thumbnail: thumb-parichay-1280x720.jpg
   शीर्षक  : लोधा समाज इंदौर की वेबसाइट अब तैयार है | lodhasamaj.org
   विवरण   :
लोधा समाज इंदौर की अपनी वेबसाइट अब तैयार है — https://lodhasamaj.org

नब्बे सेकंड में पूरी वेबसाइट: आयोजनों की तिथि और समय, तीनों आयोजनों की
वर्षवार दानदाता सूचियाँ (किसने क्या दिया, नाम और मात्रा सहित),
छात्रवृत्तियों के पोर्टल, आपातकालीन नंबर और आयुष्मान कार्ड की जानकारी,
पदाधिकारी, गैलरी, पंजीयन और संपर्क।

हिंदी और अंग्रेज़ी दोनों में। फ़ोन पर भी आसानी से चलती है।

संपर्क: +91 90987 81740
॥ जय माता दी ॥
   tags    : लोधा समाज, लोधा समाज इंदौर, Lodha Samaj, Lodha Samaj Indore,
             लोधी समाज, इंदौर, महूनाका, नवदुर्गा महोत्सव, lodhasamaj.org

   ── गरबा रील ───────────────────────────────────────────
   फ़ाइल   : assets/video/2026/garba-reel.mp4  (2 मिनट 8 सेकंड)
   thumbnail: thumb-garba-1280x720.jpg
   शीर्षक  : नवदुर्गा महोत्सव 2026 | गरबा | लोधा समाज इंदौर
   विवरण   :
नवदुर्गा महोत्सव 2026 के गरबे की झलकियाँ — 13 अक्टूबर 2026 की रात,
महाराणा प्रताप चौराहा, महूनाका इंदौर।

आयोजक: लोधा समाज इंदौर
और चित्र एवं वीडियो: https://lodhasamaj.org/hi/gallery/

॥ जय माता दी ॥
   tags    : गरबा, नवदुर्गा महोत्सव, नवरात्र 2026, लोधा समाज इंदौर,
             Garba, Navratri 2026, Indore, Mhow Naka

5. PLAYLISTS बनाइए
   47 वीडियो बिना क्रम के पड़े हैं। चार सूचियाँ काफ़ी हैं:
       नवदुर्गा महोत्सव एवं गरबा
       नगर कन्या भोज एवं विशाल भंडारा
       कावड़ यात्रा
       समाज के अन्य कार्यक्रम

6. चैनल का नाम और हैंडल
   नाम "Lodha Samaj Indore" और हैंडल @LodhaSamajIndoreOfficial ठीक हैं —
   इन्हें मत बदलिए। हैंडल बदलने पर पुराना पता मर जाता है; वेबसाइट पर अभी
   जो पुराना पता लगा था (@lodhasamajindore2762), वह इसी कारण 404 दे रहा था।

══════════════════════════════════════════════════════════
चित्र इस फ़ोल्डर में: assets/img/youtube/
दोबारा बनाने के लिए: python3 tools/make_youtube_kit.py
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8099",
                    help="a server with the repo at its root, for the screenshots")
    ap.add_argument("--text-out", type=Path, help="also write the words to this file")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    tmp = ROOT / ".youtube-kit.html"
    shutil.copyfile(ROOT / "tools" / "youtube-kit.html.in", tmp)
    try:
        shots = [[sid, name.replace(".jpg", ".png"), transparent]
                 for sid, name, _, transparent in SHOTS]
        script = CAPTURE % {"playwright": PLAYWRIGHT, "out": str(OUT),
                            "url": args.base_url.rstrip("/") + "/.youtube-kit.html",
                            "shots": repr(shots).replace("'", '"')
                                                .replace("True", "true").replace("False", "false")}
        subprocess.run(["node", "--input-type=module", "-e", script], check=True)
    finally:
        tmp.unlink(missing_ok=True)

    # Thumbnails go out as JPEG: YouTube holds them to 2 MB, and a photograph
    # under text costs far less that way. The rest stay PNG - flat colour and
    # type, which PNG keeps exactly and the watermark needs transparency.
    for _, name, what, _ in SHOTS:
        made = OUT / name.replace(".jpg", ".png")
        final = OUT / name
        if name.endswith(".jpg"):
            subprocess.run(["convert", str(made), "-strip", "-interlace", "Plane",
                            "-quality", "90", str(final)], check=True)
            made.unlink()
        else:
            subprocess.run(["mogrify", "-strip", str(final)], check=True)
        px = subprocess.run(["identify", "-format", "%wx%h", str(final)],
                            capture_output=True, text=True, check=True).stdout
        print(f"  {final.relative_to(ROOT)}  {px}  {final.stat().st_size // 1024} KB  — {what}")

    words = text_kit()
    if args.text_out:
        args.text_out.write_text(words, encoding="utf-8")
        print(f"\nwords written to {args.text_out}")
    else:
        print("\n" + words)
    return 0


if __name__ == "__main__":
    sys.exit(main())
