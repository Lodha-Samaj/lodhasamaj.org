// The गैलरी's viewer: a thumbnail opens the picture at the size it deserves.
// Each thumbnail is a button, so it works from the keyboard as well as the
// thumb; the viewer traps focus while open and hands it back on close.
import { step, slideOf, counterText } from './lightbox-core.js';

// There is a roll per year now, so every .gallery-grid on the page feeds one
// viewer: ❮ ❯ walk from the last picture of one year into the first of the next
// rather than stopping at a heading.
const grids = [...document.querySelectorAll('.gallery-grid')];
if (grids.length) {
  const lang = document.documentElement.lang.toLowerCase().startsWith('en') ? 'en' : 'hi';
  const T = lang === 'hi'
    ? { open: 'बड़ा करके देखें', close: 'बंद करें', prev: 'पिछला चित्र', next: 'अगला चित्र',
        label: 'चित्र' }
    : { open: 'View larger', close: 'Close', prev: 'Previous picture', next: 'Next picture',
        label: 'Picture' };

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Each <img> becomes the face of a button. The markup stays plain HTML for
  // anyone without JavaScript: there the pictures are simply pictures.
  const shots = grids.flatMap((g) => [...g.querySelectorAll('img')]);
  shots.forEach((img, i) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'shot';
    button.setAttribute('aria-label', `${T.open}: ${img.alt || `${T.label} ${i + 1}`}`);
    img.replaceWith(button);
    button.append(img);
    button.addEventListener('click', () => open(i));
  });
  if (!shots.length) throw new Error('gallery: no pictures to show');

  const box = document.createElement('div');
  box.className = 'lightbox';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', T.label);
  box.innerHTML = `
    <button class="lb-close" aria-label="${esc(T.close)}">×</button>
    <button class="lb-prev" aria-label="${esc(T.prev)}">❮</button>
    <figure class="lb-frame"><img alt=""><figcaption class="lb-count"></figcaption></figure>
    <button class="lb-next" aria-label="${esc(T.next)}">❯</button>`;
  document.body.append(box);

  const frame = box.querySelector('.lb-frame img');
  const count = box.querySelector('.lb-count');
  const buttons = () => [...box.querySelectorAll('button')];
  let at = 0;
  let cameFrom = null;

  function show(i) {
    at = step(i, 0, shots.length);
    const slide = slideOf(shots[at]);
    frame.src = slide.src;
    frame.alt = slide.alt;
    if (slide.width) { frame.width = slide.width; frame.height = slide.height; }
    count.textContent = counterText(at, shots.length, lang);
  }

  function open(i) {
    cameFrom = document.activeElement;
    show(i);
    box.hidden = false;
    document.body.classList.add('lb-open');
    box.querySelector('.lb-close').focus();
  }

  function close() {
    box.hidden = true;
    document.body.classList.remove('lb-open');
    // Back to the thumbnail they opened, not to the top of the page.
    (shots[at]?.closest('button') || cameFrom)?.focus();
  }

  box.querySelector('.lb-close').addEventListener('click', close);
  box.querySelector('.lb-prev').addEventListener('click', () => show(step(at, -1, shots.length)));
  box.querySelector('.lb-next').addEventListener('click', () => show(step(at, 1, shots.length)));
  // A click on the backdrop - never on the picture or a button - closes it.
  box.addEventListener('click', (event) => { if (event.target === box) close(); });

  document.addEventListener('keydown', (event) => {
    if (box.hidden || event.defaultPrevented) return;
    if (event.key === 'Escape') { close(); return; }
    if (event.key === 'ArrowLeft') { show(step(at, -1, shots.length)); return; }
    if (event.key === 'ArrowRight') { show(step(at, 1, shots.length)); return; }
    if (event.key !== 'Tab') return;
    // Hold focus inside the viewer while it is open.
    const stops = buttons();
    const edge = event.shiftKey ? stops[0] : stops[stops.length - 1];
    if (document.activeElement === edge) {
      event.preventDefault();
      (event.shiftKey ? stops[stops.length - 1] : stops[0]).focus();
    }
  });
}
