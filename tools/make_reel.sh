#!/usr/bin/env bash
# Joins the नवरात्र 2026 गरबा clips into one 9:16 reel.
#
#   usage: tools/make_reel.sh <source-dir>
#
# It reads the ORIGINALS, not the clips already in assets/video/2026/. Those
# have been through x264 once; running them through again would show it. The
# originals live in the gitignored /2026/ - see tools/encode_media.sh.
#
# The clips are in the order they were shot. Eight stand upright and one lies
# flat, so every frame is fitted inside the same 720x1280 box and whatever is
# left over is filled with a blurred, darkened copy of the frame itself: the
# flat clip keeps its whole picture instead of being cropped to a third of it,
# and nothing jumps shape mid-reel.
#
# Each clip carries its own loud music, recorded at whatever the phone was
# standing next to, so loudnorm evens the levels - without it the reel lurches
# in volume at every cut.
set -euo pipefail

src=${1:?usage: tools/make_reel.sh <source-dir>}
root=$(cd "$(dirname "$0")/.." && pwd)
out=$root/assets/video/2026
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$out"

# In the order they were shot: IMG_1245 .. IMG_1273 are the नवरात्र night,
# and the men's गरबा comes last.
CLIPS=(
  IMG_1245.MOV IMG_1246.MOV IMG_1247.MOV IMG_1248.MOV
  IMG_1256.MOV IMG_1258.MOV IMG_1259.MOV IMG_1273.MOV
  document_6235348819282764025.mp4
)

# Every piece is encoded to exactly the same shape and settings so the pieces
# can be joined without being encoded a second time.
n=0
for clip in "${CLIPS[@]}"; do
  n=$((n + 1))
  printf 'fitting %s (%d/%d)\n' "$clip" "$n" "${#CLIPS[@]}" >&2
  ffmpeg -v error -y -i "$src/$clip" -filter_complex "
      [0:v]fps=30,
           scale=w='min(1280,iw)':h='min(1280,ih)':force_original_aspect_ratio=decrease,
           hqdn3d=3:3:6:6,
           eq=contrast=1.06:brightness=0.02:saturation=1.10,
           split[a][b];
      [a]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,
         gblur=sigma=24,eq=brightness=-0.12[bg];
      [b]scale=720:1280:force_original_aspect_ratio=decrease[fg];
      [bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v];
      [0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]" \
    -map '[v]' -map '[a]' \
    -c:v libx264 -profile:v high -level 4.0 -preset slow -crf 25 \
    -maxrate 2000k -bufsize 4000k \
    -c:a aac -b:a 128k -ar 48000 -ac 2 \
    -map_metadata -1 "$work/$(printf '%02d' "$n").mp4"
  printf "file '%s'\n" "$work/$(printf '%02d' "$n").mp4" >> "$work/list.txt"
done

# Identical settings all through, so this joins them without re-encoding.
ffmpeg -v error -y -f concat -safe 0 -i "$work/list.txt" \
  -c copy -movflags +faststart "$out/garba-reel.mp4"

# The still before anyone presses play, graded and sized like the others.
ffmpeg -v error -y -ss 3 -i "$out/garba-reel.mp4" -frames:v 1 -q:v 2 "$out/garba-reel.jpg"
mogrify -colorspace sRGB -contrast-stretch 0.25%x0.02% \
  -modulate 104,107,100 -sigmoidal-contrast 2.5,47% \
  -unsharp 0x0.8+0.6+0.02 -resize '760x760>' \
  -strip -interlace Plane -quality 80 "$out/garba-reel.jpg"

echo "---"
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height -of default=nw=1 "$out/garba-reel.mp4"
