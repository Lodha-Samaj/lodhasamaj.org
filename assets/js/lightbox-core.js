// Pure gallery-viewer logic. No DOM, no events - so it is testable with node:test.

/** The picture `delta` steps from `index`, coming round at either end.
 *  Anything that is not a usable position falls back to the first picture. */
export function step(index, delta, count) {
  const n = Number(count);
  const i = Number(index);
  if (!Number.isInteger(n) || n < 1 || !Number.isFinite(i)) return 0;
  return ((Math.trunc(i) + Number(delta || 0)) % n + n) % n;
}

/** What the viewer needs from a thumbnail. The size comes from the loaded
 *  image so the big frame can hold its shape before the full picture lands. */
export function slideOf(img) {
  return {
    src: img?.src || '',
    alt: img?.alt || '',
    width: img?.naturalWidth || 0,
    height: img?.naturalHeight || 0,
  };
}

/** "12 में से 3" / "3 of 12" - said the way each language counts. */
export function counterText(index, count, lang) {
  const shown = step(index, 0, count) + 1;
  return lang === 'hi' ? `${count} में से ${shown}` : `${shown} of ${count}`;
}
