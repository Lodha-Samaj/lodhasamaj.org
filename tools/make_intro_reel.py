#!/usr/bin/env python3
"""Cuts the website-introduction reel: narration, page captures, end card.

    # read by a person (preferred):
    python3 tools/make_intro_reel.py --voice-file <recording> --shots <dir>

    # spoken by the machine:
    python3 tools/make_intro_reel.py --piper <venv-python> --voices <dir> \
        --shots <dir> [--out assets/video/2026/parichay-reel.mp4]

    # the sheet to read from, printed from the same script:
    python3 tools/make_intro_reel.py --reading-sheet

What it needs, none of which belongs in the repository:
  * a narrator - either a recording (--voice-file) or a Piper voice
    (`pip install piper-tts`, then `python -m piper.download_voices
    hi_IN-priyamvada-medium`). A person reading it is better and this is a
    समाज's own website, so --voice-file is the one to reach for;
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


def to_wav(src: Path, out: Path):
    """Whatever the phone produced - .opus, .m4a, .mp3 - becomes one mono wav,
    with the dead air at either end trimmed and the level evened out."""
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-af", "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB,"
                "areverse,silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB,"
                "areverse,loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ac", "1", "-ar", "48000", str(out)])


def pauses_in(wav: Path, floor_db: int = -38, shortest: float = 0.30):
    """Every silence in the recording, as (middle, length), longest first."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(wav),
         "-af", f"silencedetect=noise={floor_db}dB:d={shortest}", "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    starts, found = [], []
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            starts.append(float(line.rsplit("silence_start:", 1)[1].strip()))
        elif "silence_end:" in line and starts:
            end, _, dur = line.rsplit("silence_end:", 1)[1].partition("|")
            begin = starts.pop()
            found.append(((begin + float(end)) / 2, float(end) - begin))
    return sorted(found, key=lambda p: -p[1])


def split_recording(wav: Path, segments, work: Path):
    """Give each written line the slice of the recording where it was read.

    The reader is asked to leave a clear pause between lines, so the cuts are
    the longest silences: with n lines we want the n-1 longest, in time order.
    If the recording does not hold that many - the reader ran lines together,
    or the room was noisy - say so and fall back to splitting by how long each
    line is to say, which keeps the film in step with the words even when it
    cannot land on the breath.
    """
    total = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(wav)], capture_output=True, text=True,
        check=True).stdout.strip().rstrip(","))
    wanted = len(segments) - 1
    found = pauses_in(wav)
    if len(found) >= wanted:
        cuts = sorted(p[0] for p in found[:wanted])
        how = f"{len(found)} pauses found, used the {wanted} longest"
    else:
        weight = [len(seg["say"]) for seg in segments]
        running, cuts = 0, []
        for w in weight[:-1]:
            running += w
            cuts.append(total * running / sum(weight))
        how = (f"WARNING: only {len(found)} clear pauses for {wanted} line breaks - "
               "split by line length instead. Re-record with a fuller pause "
               "between lines if the picture lags the words.")
    print(f"  {how}")

    edges = [0.0] + cuts + [total]
    for i, seg in enumerate(segments, 1):
        piece = work / f"say-{i:02d}.wav"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(wav),
             "-ss", f"{edges[i-1]:.3f}", "-to", f"{edges[i]:.3f}",
             "-c", "copy", str(piece)])
        seg["wav"] = piece
        seg["seconds"] = duration_of(piece)
    return total


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


def reading_sheet(spec) -> str:
    """The script as something to read from, not as JSON.

    It is numbered because the pause between numbers is what lets the picture
    be cut to the reading afterwards, and it says so at the top rather than
    leaving the reader to guess why the lines are broken up this way.
    """
    out = [
        "लोधा समाज इंदौर — वेबसाइट परिचय, पढ़ने की शीट",
        "",
        "कैसे पढ़ें:",
        "  • शांत कमरे में, फ़ोन मुँह से एक बित्ता दूर। पंखा और कूलर बंद।",
        "  • हर अंकित पंक्ति के बाद एक पूरी साँस रुकें — लगभग एक सेकंड।",
        "    यही ठहराव बताता है कि चित्र कब बदलना है, इसलिए यह ज़रूरी है।",
        "  • एक ही बार में पूरा पढ़ें। बीच में अटकें तो रुकिए मत — उसी पंक्ति को",
        "    फिर से पढ़ दीजिए, बाद में काट दिया जाएगा।",
        "  • सहज गति से। पूरा पढ़ने में लगभग डेढ़ मिनट लगना चाहिए।",
        "",
        "—" * 34,
        "",
    ]
    for i, seg in enumerate(spec["segments"], 1):
        out.append(f"{i:2d}.  {seg['say']}")
        out.append("")
    out += [
        "—" * 34,
        "",
        "कुछ शब्द जैसे बोलने हैं वैसे ही लिखे हैं — \"लोधासमाज डॉट ओ आर जी\",",
        "\"छियालीसवाँ\", \"नौ शून्य नौ आठ...\" — वैसे ही पढ़िए, अंकों में नहीं।",
    ]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice-file", type=Path,
                    help="a recording of someone reading the script, in any format "
                         "ffmpeg opens. Preferred over --piper.")
    ap.add_argument("--piper", help="python of the venv holding piper-tts")
    ap.add_argument("--voices", type=Path, help="directory of .onnx voices")
    ap.add_argument("--shots", type=Path, help="stills from reel-intro-capture.mjs")
    ap.add_argument("--reading-sheet", action="store_true",
                    help="print the lines to read aloud, numbered, and stop")
    ap.add_argument("--script", type=Path, default=ROOT / "tools" / "reel-intro-script.json")
    ap.add_argument("--out", type=Path, default=ROOT / "assets" / "video" / "2026" / "parichay-reel.mp4")
    ap.add_argument("--target", type=float, default=90.0, help="intended length, seconds")
    # Trying a different narrator should not mean editing the script, and the
    # two go together: a slower voice reading the same words runs long, so the
    # pace usually has to move with it.
    ap.add_argument("--voice", help="override the voice named in the script")
    ap.add_argument("--length-scale", type=float, help="override the pace; >1 is slower")
    args = ap.parse_args()

    spec = json.loads(args.script.read_text(encoding="utf-8"))
    if args.reading_sheet:
        print(reading_sheet(spec))
        return 0
    if not args.shots:
        ap.error("--shots is required")
    if not args.voice_file and not (args.piper and args.voices):
        ap.error("give --voice-file, or --piper together with --voices")
    if args.voice:
        spec["voice"] = args.voice
    if args.length_scale:
        spec["lengthScale"] = args.length_scale
    gap = float(spec["gapSeconds"])

    model = None
    if not args.voice_file:
        model = args.voices / (spec["voice"] + ".onnx")
        if not model.exists():
            print(f"no such voice: {model}", file=sys.stderr)
            return 1

    work = Path(tempfile.mkdtemp(prefix="intro-reel-"))
    try:
        if args.voice_file:
            # 1. A person read it. Find where each line ends and cut there, so
            #    the picture follows their pauses rather than a clock.
            to_wav(args.voice_file, work / "read.wav")
            split_recording(work / "read.wav", spec["segments"], work)
            for i, seg in enumerate(spec["segments"], 1):
                print(f"  {i:02d} {seg['seconds']:5.2f}s  {seg['shot']}")
            # The reader's own pauses are already in the recording, so nothing
            # is inserted between the lines - the narration IS the recording.
            shutil.copyfile(work / "read.wav", work / "voice.wav")
            gap = 0.0
        else:
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
        # --out may point outside the repo (a trial cut), so do not assume it is under it.
        shown = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
        print(f"\n{shown}  {length:.1f}s  {size/1048576:.1f} MB"
              f"   (narration {spoken:.1f}s, target {args.target:.0f}s,"
              f" out by {abs(length - args.target):.1f}s)")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
