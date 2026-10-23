#!/usr/bin/env python3
"""Cuts the दानदाता reel: title, totals, every name rolling past, धन्यवाद.

    python3 tools/make_donor_reel.py [--year 2026]
        [--out assets/video/2026/daan-reel-2026.mp4]

The cards are shots of tools/donor-reel.html.in, which reads the year's list
and words it with the दान page's own code, so re-running this after a list
changes is all it takes to bring the reel up to date - nothing is typed twice.
It serves the repo itself on a free local port for the shoot and stops after.

The roll is one tall picture of the whole list, slid upward under a fixed band.
Its speed is the one number chosen by a person (--px-per-sec); the roll lasts
as long as the list needs at that speed, and the script reports the length.

The sound is the men's गरबा from the नवरात्र reel: the last 45 seconds of
garba-reel.mp4 are one uncut take, so the music never jumps at a cut. A reel
longer than that take is refused rather than looped - lower --px-per-sec's
reading time some other way, or pass --music.
"""
import argparse
import functools
import http.server
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
PLAYWRIGHT = Path.home() / ".npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js"

# The uncut men's गरबा: tools/make_reel.sh puts that clip last, from 81.4 s.
MUSIC = ROOT / "assets/video/2026/garba-reel.mp4"
MUSIC_FROM, MUSIC_LONGEST = 81.6, 45.5

TITLE_S, TOTALS_S, THANKS_S, FADE_S = 4.5, 5.5, 6.0, 0.5
# The opening hold includes the fade in, so it is the longer of the two.
ROLL_HOLD = (1.5, 1.0)

H264 = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
        "-preset", "slow", "-crf", "22",
        "-maxrate", "2500k", "-bufsize", "5000k", "-pix_fmt", "yuv420p"]

CAPTURE = r"""
import pw from '%(playwright)s';
const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
const p = await b.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });
for (const shot of ['title', 'totals', 'roll', 'band', 'thanks']) {
  await p.goto(`%(base)s/.donor-reel.html?year=%(year)s&shot=${shot}`, { waitUntil: 'networkidle' });
  await p.waitForSelector('body[data-ready]');
  await p.waitForTimeout(400);
  await p.screenshot({ path: `%(out)s/${shot}.png`, fullPage: shot === 'roll',
                       omitBackground: shot === 'band' });
  console.log(shot);
}
await b.close();
"""


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def serve(root: Path) -> http.server.ThreadingHTTPServer:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def shoot(year: str, shots: Path, playwright: Path) -> None:
    card = ROOT / ".donor-reel.html"
    shutil.copyfile(ROOT / "tools" / "donor-reel.html.in", card)
    srv = serve(ROOT)
    try:
        script = CAPTURE % {"playwright": playwright, "year": year, "out": shots,
                            "base": f"http://127.0.0.1:{srv.server_address[1]}"}
        run(["node", "--input-type=module", "-e", script])
    finally:
        srv.shutdown()
        card.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2026")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--px-per-sec", type=float, default=320,
                    help="roll speed in output pixels; a little over three names a second")
    ap.add_argument("--music", type=Path, help="any audio file, used from its start")
    ap.add_argument("--playwright", type=Path, default=PLAYWRIGHT)
    args = ap.parse_args(argv)
    out = args.out or ROOT / f"assets/video/{args.year}/daan-reel-{args.year}.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        shots = Path(tmp)
        shoot(args.year, shots, args.playwright)

        roll_h = Image.open(shots / "roll.png").height
        travel = roll_h - H
        # Held still for a moment at each end: the first names have to be read
        # before they move, and the last ones before the cut takes them.
        roll_s = round(ROLL_HOLD[0] + travel / args.px_per_sec + ROLL_HOLD[1], 2)
        total = TITLE_S + TOTALS_S + roll_s + THANKS_S - 3 * FADE_S
        music, music_from = (args.music, 0.0) if args.music else (MUSIC, MUSIC_FROM)
        if not args.music and total > MUSIC_LONGEST:
            print(f"the reel would run {total:.1f} s, past the {MUSIC_LONGEST} s of uncut "
                  f"music; raise --px-per-sec or pass --music", file=sys.stderr)
            return 1

        # The cards drift in slowly so a held card does not look frozen. Each is
        # one frame in, and zoompan makes all of its frames from it; it is fed a
        # doubled frame because at 1:1 its rounding shimmers.
        def drift(seconds, step):
            n = round(seconds * FPS)
            return (f"scale={2 * W}:{2 * H},zoompan=z='1+{step}*on':d={n}:"
                    f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s={W}x{H}:fps={FPS},setsar=1")

        graph = ";".join([
            f"[0:v]{drift(TITLE_S, 0.0004)}[t]",
            f"[1:v]{drift(TOTALS_S, 0.0003)}[s]",
            f"[2:v]fps={FPS},crop={W}:{H}:0:'min({travel},max(0,(t-{ROLL_HOLD[0]})*{args.px_per_sec}))',"
            f"setsar=1[r0];[r0][3:v]overlay=0:0:shortest=1[r]",
            f"[4:v]{drift(THANKS_S, 0.0003)}[k]",
            f"[t][s]xfade=fade:duration={FADE_S}:offset={TITLE_S - FADE_S}[ts]",
            f"[ts][r]xfade=fade:duration={FADE_S}:offset={TITLE_S + TOTALS_S - 2 * FADE_S}[tr]",
            f"[tr][k]xfade=fade:duration={FADE_S}:"
            f"offset={TITLE_S + TOTALS_S + roll_s - 3 * FADE_S}[v0]",
            "[v0]format=yuv420p[v]",
            f"[5:a]atrim=0:{total},asetpts=N/SR/TB,afade=t=in:d=1.2,"
            f"afade=t=out:st={total - 3}:d=3,aresample=48000[a]",
        ])
        out.parent.mkdir(parents=True, exist_ok=True)
        held = ["-loop", "1", "-framerate", str(FPS), "-t", str(roll_s + 1)]
        run(["ffmpeg", "-v", "error", "-y",
             "-i", str(shots / "title.png"),
             "-i", str(shots / "totals.png"),
             *held, "-i", str(shots / "roll.png"),
             *held, "-i", str(shots / "band.png"),
             "-i", str(shots / "thanks.png"),
             "-ss", str(music_from), "-i", str(music),
             "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
             *H264, "-r", str(FPS), "-c:a", "aac", "-b:a", "128k", "-ac", "2",
             "-movflags", "+faststart", "-map_metadata", "-1", "-t", str(total), str(out)])

        poster = out.with_suffix(".jpg")
        run(["convert", str(shots / "title.png"), "-resize", "540x960", "-strip",
             "-interlace", "Plane", "-quality", "86", str(poster)])

    print(f"{out.relative_to(ROOT)}  {total:.1f} s  {out.stat().st_size // 1024} KB "
          f"(roll {roll_s:.1f} s over {roll_h} px)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
