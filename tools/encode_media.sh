#!/usr/bin/env bash
# Turns the phone files the समाज sends into what the site can serve.
#
# The originals are far too heavy to publish or even to keep in git: the 2026
# नवरात्र clips are 4K60 HEVC, 50-140 MB each, and GitHub refuses a file over
# 100 MB. So the originals stay on the maintainer's disk (2026/ is gitignored)
# and only these derivatives are committed.
#
#   usage: tools/encode_media.sh <source-dir>
#
# Every output is re-encoded with its metadata dropped (-map_metadata -1 /
# -strip). That is not only for weight: the iPhone clips carry the GPS fix of
# the धर्मशाला in every frame's container, and a published file should not.
set -euo pipefail

src=${1:?usage: tools/encode_media.sh <source-dir>}
root=$(cd "$(dirname "$0")/.." && pwd)
img=$root/assets/img/gallery/2026
vid=$root/assets/video/2026
poster=$root/assets/img/karyakram
mkdir -p "$img" "$vid" "$poster"

# A still: long side 1600px, stripped, progressive.
#
# $3, if given, is a crop applied before anything else (ImageMagick geometry,
# e.g. 90%x100%+5%+0 or 1100x900+100+40), to take clutter off an edge.
photo() {
  convert "$src/$1" -auto-orient ${3:+-crop "$3" +repage} \
    -resize '1600x1600>' -strip -interlace Plane -quality 85 "$2"
}

# The same, plus the tone pass the night photographs need. They were shot after
# dark with a phone: the प्रतिमा is white शोलापीठ but comes out grey and warm
# under the tent lamps. -contrast-stretch finds the real black and white points
# (a hair on each end, so no highlight is blown), -modulate lifts and warms a
# touch, the sigmoidal curve puts back the contrast a night shot loses, and the
# unsharp mask is small - enough to bring back the carving, not enough to show.
# A poster or a printed board is NOT run through this: it is already flat art.
photo_night() {
  convert "$src/$1" -auto-orient ${3:+-crop "$3" +repage} \
    -colorspace sRGB -contrast-stretch 0.25%x0.02% \
    -modulate 104,107,100 -sigmoidal-contrast 2.5,47% \
    -unsharp 0x0.8+0.6+0.02 \
    -resize '1600x1600>' -strip -interlace Plane -quality 85 "$2"
}

# A video's still gets the same treatment, so the frame on the page is not
# muddier than the clip behind it. It is also cut to 760px: a poster is the one
# thing the page DOES fetch for every clip before anyone presses play, and ten
# of them at full frame size came to 1.2 MB on a phone that may never play one.
grade() {
  mogrify -colorspace sRGB -contrast-stretch 0.25%x0.02% \
    -modulate 104,107,100 -sigmoidal-contrast 2.5,47% \
    -unsharp 0x0.8+0.6+0.02 -resize '760x760>' \
    -strip -interlace Plane -quality 80 "$1"
}

# A clip: long side at most 1280px, 30fps, H.264 High + AAC mono so every phone
# plays it, and +faststart so it begins before the whole file has landed.
#
# Three choices worth keeping: the scale never enlarges (two of these clips
# arrive at 464x848 and upscaling them only costs bytes); hqdn3d takes out the
# sensor noise, which is what a 4K phone clip shot after dark spends most of its
# bitrate on; and -maxrate holds the result near 2 Mbps, because someone in
# इंदौर is watching this on mobile data, not on a desk.
clip() {
  ffmpeg -v error -y -i "$src/$1" \
    -vf "scale=w='min(1280,iw)':h='min(1280,ih)':force_original_aspect_ratio=decrease,fps=30,hqdn3d=3:3:6:6" \
    -c:v libx264 -profile:v high -level 4.0 -preset slow -crf 26 \
    -maxrate 2000k -bufsize 4000k -pix_fmt yuv420p \
    -c:a aac -b:a 96k -ac 1 -ar 44100 \
    -map 0:v:0 -map 0:a:0 -map_metadata -1 -movflags +faststart "$2"
  # The still shown before anyone presses play. A second in by default, so it
  # is not the black frame a phone opens on; $3 moves it when that second
  # happens to be a hand swung across the lens.
  ffmpeg -v error -y -ss "${3:-1}" -i "$2" -frames:v 1 -q:v 2 "${2%.mp4}.jpg"
  grade "${2%.mp4}.jpg"
}

# The crops take the pandal's surroundings off the edges - a shop board, a
# stack of bricks, the neighbouring wall - so each frame holds the प्रतिमा and
# nothing that distracts from it.
photo_night photo_6235348819742757518_y.jpg "$img/pratima-1.jpg" '89%x100%+11%+0'
photo_night photo_6235348819742757519_y.jpg "$img/pratima-2.jpg"
photo_night photo_6235348819742757521_y.jpg "$img/pratima-3.jpg" '94%x100%+6%+0'
photo_night photo_6235348819742757523_y.jpg "$img/pratima-4.jpg"
photo_night photo_6235348819742757525_y.jpg "$img/pratima-5.jpg"

# The two announcement boards for the 23 October भंडारा. They live with the
# कार्यक्रम page, not in the गैलरी roll: they are an invitation, not a photograph.
photo photo_6228687252452218305_y.jpg "$poster/bhandara-2026.jpg"
photo photo_6228687252452218306_y.jpg "$poster/bhandara-2026-nimantran.jpg"

clip IMG_1245.MOV "$vid/garba-1.mp4"
clip IMG_1246.MOV "$vid/garba-2.mp4" 6
clip IMG_1247.MOV "$vid/garba-3.mp4"
clip IMG_1248.MOV "$vid/garba-4.mp4"
clip IMG_1256.MOV "$vid/garba-5.mp4"
clip IMG_1258.MOV "$vid/garba-6.mp4"
clip IMG_1259.MOV "$vid/garba-7.mp4"
clip IMG_1273.MOV "$vid/garba-8.mp4"
clip document_6235348819282764025.mp4 "$vid/garba-purush.mp4" 21
clip document_6235348819282764027.mp4 "$vid/nasha-mukti-pratigya.mp4"

echo "---"
du -ch "$img" "$vid" "$poster" | tail -4
