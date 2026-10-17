#!/usr/bin/env python3
"""Builds the two pictures the साझा page hands out: a QR code and a square card.

    python3 tools/make_share_assets.py [--base-url http://127.0.0.1:8099]

The QR is drawn here rather than fetched from one of the free QR services,
because such a service can rewrite where the code points - or stop answering -
long after the sticker is printed. This one encodes the address itself and
nothing else, so it keeps working with nobody's permission.

The card is a page screenshot for the same reason the reel's end card is: it
carries the site's own logo, colours and fonts, so what people see before they
tap is what they find after. It needs the site's /assets/ to resolve, so it is
copied to a dot-path at the root for one shot and removed - see the note in
tools/share-card.html.in.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://lodhasamaj.org/"
OUT = ROOT / "assets" / "img" / "share"

CAPTURE = r"""
import pw from '%(playwright)s';
const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
const p = await b.newPage({ viewport: { width: 540, height: 540 }, deviceScaleFactor: 2 });
await p.goto('%(url)s', { waitUntil: 'networkidle' });
await p.waitForTimeout(900);
await p.screenshot({ path: '%(out)s' });
await b.close();
"""
PLAYWRIGHT = "/home/sverma/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8099",
                    help="a server with the repo at its root, for the card screenshot")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    # -m 4 is the quiet zone the QR spec asks for, and this PNG is the one that
    # gets printed on a notice or a card, where whatever surrounds it is out of
    # our hands. A narrower zone still reads on a bright screen and then fails
    # on paper, which is the worst way for it to fail - nobody re-checks a
    # sticker. -l M survives a fair amount of wear before it stops decoding.
    qr = OUT / "qr-lodhasamaj.png"
    subprocess.run(["qrencode", "-o", str(qr), "-s", "12", "-m", "4",
                    "-l", "M", "--foreground=241F2E", SITE], check=True)
    subprocess.run(["mogrify", "-strip", str(qr)], check=True)
    print(f"{qr.relative_to(ROOT)}  {qr.stat().st_size // 1024} KB")

    tmp = ROOT / ".share-card.html"
    shutil.copyfile(ROOT / "tools" / "share-card.html.in", tmp)
    try:
        png = OUT / "share-card.png"
        script = CAPTURE % {"playwright": PLAYWRIGHT,
                            "url": args.base_url.rstrip("/") + "/.share-card.html",
                            "out": str(png)}
        subprocess.run(["node", "--input-type=module", "-e", script], check=True)
    finally:
        tmp.unlink(missing_ok=True)

    card = OUT / "share-card.jpg"
    subprocess.run(["convert", str(png), "-strip", "-interlace", "Plane",
                    "-quality", "88", str(card)], check=True)
    png.unlink()
    print(f"{card.relative_to(ROOT)}  {card.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
