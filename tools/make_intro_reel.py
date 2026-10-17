#!/usr/bin/env python3
"""Cuts the website-introduction reel: narration, page captures, end card.

    python3 tools/make_intro_reel.py --piper <venv-python> --voices <dir> \
        --shots <dir> [--out assets/video/2026/parichay-reel.mp4]

What it needs, none of which belongs in the repository:
  * a Piper voice (`pip install piper-tts`, then `python -m piper.download_voices
    hi_IN-pratham-medium`) - the narration is spoken, not recorded;
  * the stills from tools/reel-intro-capture.mjs, which drives a browser over
    the real pages so the film shows the site as it is, not a mock-up;
  * assets/video/2026/garba-reel.mp4, for the one shot that moves.

The picture is cut TO the narration, never the other way round: each line is
spoken first, its length measured, and the shot under it held exactly that long.
So a line can be rewritten without re-timing anything by hand - the only number
chosen by a person is the 90 seconds in --target, and the script reports how far
off it came out.

Consecutive lines that name the same shot share one take, so the cut falls where
the subject changes rather than every time the speaker breathes.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30

# Every take is encoded identically so they can be joined without a second pass.
# The cap is what keeps the finished film small enough to send on WhatsApp; the
# picture is mostly page text held still, which h264 carries cheaply, so the cap
# is never what decides the quality - the slow drift across the frame is.
H264 = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
        "-preset", "slow", "-crf", "23",
        "-maxrate", "1800k", "-bufsize", "3600k", "-pix_fmt", "yuv420p"]


def run(cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def duration_of(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def speak(piper: str, model: Path, text: str, length_scale: float, out: Path) -> float:
    subprocess.run([piper, "-m", "piper", "-m", str(model),
                    "--length-scale", str(length_scale), "-f", str(out)],
                   input=text, text=True, check=True, capture_output=True)
    return duration_of(out)


def silence(seconds: float, rate: int, out: Path):
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r={rate}:cl=mono", "-t", f"{seconds:.3f}", str(out)])


def group_shots(segments, gap):
    """One take per run of consecutive lines sharing a shot, with its length."""
    takes = []
    for seg in segments:
        if takes and takes[-1]["shot"] == seg["shot"]:
            takes[-1]["seconds"] += seg["seconds"] + gap
        else:
            takes.append({"shot": seg["shot"], "seconds": seg["seconds"] + gap})
    return takes


def still_take(src: Path, seconds: float, out: Path, zoom_in: bool):
    """A still, held for `seconds`, drifting slowly in or out.

    The source is doubled before the move and the result taken back down to
    1080x1920. zoompan steps the crop by whole source pixels, which on a frame
    the size of the output judders visibly; with twice the pixels to step
    through, the same move lands on half-pixels of the output and reads smooth.
    """
    frames = max(2, int(round(seconds * FPS)))
    span = 0.07
    # zoompan's z is evaluated per frame; 'on' is the output frame number.
    z = (f"1+{span}*on/{frames}" if zoom_in else f"{1 + span}-{span}*on/{frames}")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(src),
         "-filter_complex",
         f"[0:v]scale={W*2}:{H*2}:flags=lanczos,"
         f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
         f":s={W*2}x{H*2}:fps={FPS},"
         f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p[v]",
         "-map", "[v]", "-frames:v", str(frames),
         *H264, str(out)])


def video_take(src: Path, start: float, seconds: float, out: Path):
    """A piece of the गरबा reel, fitted to 9:16 and silent - the only voice in
    this film is the narrator's."""
    frames = max(2, int(round(seconds * FPS)))
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start}", "-i", str(src),
         "-an", "-filter_complex",
         f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
         f"crop={W}:{H},setsar=1,format=yuv420p[v]",
         "-map", "[v]", "-frames:v", str(frames),
         *H264, str(out)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--piper", required=True, help="python of the venv holding piper-tts")
    ap.add_argument("--voices", required=True, type=Path, help="directory of .onnx voices")
    ap.add_argument("--shots", required=True, type=Path, help="stills from reel-intro-capture.mjs")
    ap.add_argument("--script", type=Path, default=ROOT / "tools" / "reel-intro-script.json")
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "video" / "2026" / "parichay-reel.mp4")
    ap.add_argument("--target", type=float, default=90.0, help="intended length, seconds")
    args = ap.parse_args()

    spec = json.loads(args.script.read_text(encoding="utf-8"))
    model = args.voices / (spec["voice"] + ".onnx")
    if not model.exists():
        print(f"no such voice: {model}", file=sys.stderr)
        return 1
    gap = float(spec["gapSeconds"])

    work = Path(tempfile.mkdtemp(prefix="intro-reel-"))
    try:
        # 1. Speak every line and learn how long it is.
        for i, seg in enumerate(spec["segments"], 1):
            wav = work / f"say-{i:02d}.wav"
            seg["seconds"] = speak(args.piper, model, seg["say"], spec["lengthScale"], wav)
            seg["wav"] = wav
            print(f"  {i:02d} {seg['seconds']:5.2f}s  {seg['shot']}")

        rate = wave.open(str(spec["segments"][0]["wav"])).getframerate()
        silence(gap, rate, work / "gap.wav")

        # 2. The narration: every line, each followed by the same short rest.
        listing = work / "audio.txt"
        listing.write_text("".join(
            f"file '{seg['wav']}'\nfile '{work / 'gap.wav'}'\n" for seg in spec["segments"]),
            encoding="utf-8")
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(work / "voice.wav")])
        spoken = duration_of(work / "voice.wav")

        # 3. One take per shot, each exactly as long as the lines it carries.
        takes = group_shots(spec["segments"], gap)
        parts = []
        for n, take in enumerate(takes, 1):
            part = work / f"take-{n:02d}.mp4"
            if take["shot"] == "gallery-reel":
                # Three seconds in, past the opening frames, where it is dancing.
                video_take(ROOT / "assets/video/2026/garba-reel.mp4", 3.0, take["seconds"], part)
            else:
                still = args.shots / f"{take['shot']}.png"
                if not still.exists():
                    print(f"missing still: {still}", file=sys.stderr)
                    return 1
                # Alternate the drift so the film does not pulse one way throughout.
                still_take(still, take["seconds"], part, zoom_in=(n % 2 == 1))
            parts.append(part)
            print(f"  take {n:02d} {take['seconds']:5.2f}s  {take['shot']}")

        listing = work / "video.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(work / "picture.mp4")])

        # 4. Picture and narration together. -shortest guards against the two
        #    drifting apart by a frame on the last take.
        args.out.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y",
             "-i", str(work / "picture.mp4"), "-i", str(work / "voice.wav"),
             "-c:v", "copy",
             "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-map", "0:v:0", "-map", "1:a:0", "-shortest",
             "-map_metadata", "-1", "-movflags", "+faststart", str(args.out)])

        # 5. The still shown before anyone presses play: the end card, which is
        #    the one frame that says where to go.
        poster = args.out.with_suffix(".jpg")
        shutil.copyfile(args.shots / "closing.png", work / "poster.png")
        run(["ffmpeg", "-v", "error", "-y", "-i", str(work / "poster.png"),
             "-vf", "scale=760:-2", "-q:v", "3", str(poster)])
        run(["mogrify", "-strip", str(poster)])

        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "format=duration,size", "-of", "csv=p=0:nk=1", str(args.out)],
                             capture_output=True, text=True, check=True).stdout
        # One row, comma separated - not whitespace, whatever the field order.
        length, size = (float(x) for x in out.strip().split(","))
        print(f"\n{args.out.relative_to(ROOT)}  {length:.1f}s  {size/1048576:.1f} MB"
              f"   (narration {spoken:.1f}s, target {args.target:.0f}s,"
              f" out by {abs(length - args.target):.1f}s)")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
