#!/usr/bin/env bash
# Download the two typefaces into assets/fonts/ as woff2 so the site has no
# third-party font dependency at runtime. Run once. Also fetches the SIL OFL
# licence texts, which must accompany the redistributed files.
set -euo pipefail
mkdir -p "$(dirname "$0")/../assets/fonts"
cd "$(dirname "$0")/../assets/fonts"

base="https://raw.githubusercontent.com/google/fonts/main"
curl -fsSL -O "$base/ofl/tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf"
for w in Regular SemiBold Bold ExtraBold; do
  curl -fsSL -O "$base/ofl/mukta/Mukta-$w.ttf"
done
curl -fsSL -o OFL-TiroDevanagariHindi.txt "$base/ofl/tirodevanagarihindi/OFL.txt"
curl -fsSL -o OFL-Mukta.txt "$base/ofl/mukta/OFL.txt"

# Convert to woff2 and drop the TTF originals; only woff2 is shipped.
for f in *.ttf; do
  python3 -m fontTools.ttLib.woff2 compress -o "${f%.ttf}.woff2" "$f"
  rm "$f"
done
ls -la
