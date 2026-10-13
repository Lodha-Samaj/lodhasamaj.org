import { displayNameParts, formatItems, donorTypes, typeLabel, initialOf } from './donors-core.js';

const AUTOPLAY_MS = 10000;

/** Pure: wrap an index, tolerating a stale index after the filter changed. */
export function nextIndex(current, delta, length) {
  if (length <= 0) return 0;
  if (current >= length) return delta > 0 ? 0 : length - 1;
  return (current + delta + length) % length;
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const LABELS = {
  hi: { close: 'बंद करें', prev: 'पिछला', next: 'अगला', play: 'चलाएँ', pause: 'रोकें', of: 'में से' },
  en: { close: 'Close', prev: 'Previous', next: 'Next', play: 'Play', pause: 'Pause', of: 'of' },
};

export function initModal(grid, getVisible, lang, year) {
  const T = LABELS[lang];
  let index = 0;
  let timer = null;
  let lastFocused = null;

  const modal = document.createElement('div');
  modal.className = 'donor-modal';
  modal.hidden = true;
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'dm-name');
  modal.innerHTML = `
    <div class="donor-modal-box">
      <button class="dm-close" aria-label="${esc(T.close)}">×</button>
      <p class="dm-counter"></p>
      <div class="dm-progress"><div class="dm-bar"></div></div>
      <div class="dm-avatar"></div>
      <h2 class="dm-name" id="dm-name" tabindex="-1"></h2>
      <p class="dm-type"></p>
      <p class="dm-items"></p>
      <div class="dm-controls">
        <button class="dm-prev" aria-label="${esc(T.prev)}">❮</button>
        <button class="dm-play" aria-label="${esc(T.play)}">►</button>
        <button class="dm-next" aria-label="${esc(T.next)}">❯</button>
      </div>
    </div>`;
  document.body.appendChild(modal);

  const $ = (sel) => modal.querySelector(sel);
  const bar = $('.dm-bar');

  function show() {
    const donors = getVisible();
    if (!donors.length) return close();
    index = nextIndex(index, 0, donors.length);
    const donor = donors[index];
    const avatar = $('.dm-avatar');
    if (donor.photo) {
      const img = document.createElement('img');
      img.setAttribute('src', donor.photo);
      img.setAttribute('alt', '');
      avatar.replaceChildren(img);
    } else {
      avatar.textContent = initialOf(donor);
    }
    const parts = displayNameParts(donor, lang);
    const nameEl = $('.dm-name');
    nameEl.textContent = parts.prefix ? `${parts.prefix} ` : '';
    if (parts.hindi) {
      const span = document.createElement('span');
      span.setAttribute('lang', 'hi');
      span.textContent = parts.name;
      nameEl.append(span);
    } else {
      nameEl.append(parts.name);
    }
    $('.dm-type').textContent = donorTypes(donor).map((c) => typeLabel(c, lang)).join(' · ');
    $('.dm-items').textContent = formatItems(donor, lang);
    // Hindi reads "total में से n"; English reads "n of total".
    const position = lang === 'hi'
      ? `${donors.length} ${T.of} ${index + 1}`
      : `${index + 1} ${T.of} ${donors.length}`;
    // A named list has no year to show after the position.
    $('.dm-counter').textContent = year ? `${position} · ${year}` : position;
    bar.style.transition = 'none';
    bar.style.width = '0%';
    if (timer) requestAnimationFrame(() => {
      if (!timer) return;
      bar.style.transition = `width ${AUTOPLAY_MS}ms linear`;
      bar.style.width = '100%';
    });
  }

  // Keep the real tick and the progress bar in step: any redraw while
  // autoplaying restarts the interval together with the bar.
  function restartTimer() {
    clearInterval(timer);
    timer = setInterval(() => step(1), AUTOPLAY_MS);
  }

  function step(delta) {
    index = nextIndex(index, delta, getVisible().length);
    if (timer) restartTimer();
    show();
  }

  function play() {
    if (timer) return;
    restartTimer();
    $('.dm-play').textContent = '❚❚';
    $('.dm-play').setAttribute('aria-label', T.pause);
    show();
  }

  function pause() {
    clearInterval(timer);
    timer = null;
    $('.dm-play').textContent = '►';
    $('.dm-play').setAttribute('aria-label', T.play);
    bar.style.transition = 'none';
    bar.style.width = '0%';
  }

  function open(i, origin) {
    lastFocused = origin;
    index = i;
    modal.hidden = false;
    show();
    $('.dm-name').focus();            // move focus into the dialog
  }

  function close() {
    pause();
    modal.hidden = true;
    // Return focus where it was. A filter change behind the modal may have
    // repainted that card away: try the donor that was showing, then the
    // first card, then the search box, so focus is never dropped to <body>.
    const target = (lastFocused && lastFocused.isConnected ? lastFocused : null)
      || grid.querySelector(`[data-index="${index}"]`)
      || grid.querySelector('.donor-open')
      || document.getElementById('q');
    if (target) target.focus();
  }

  grid.addEventListener('click', (event) => {
    const button = event.target.closest('.donor-open');
    // Take the origin from the click, not document.activeElement: Safari
    // does not focus a button on mouse click.
    if (button) open(Number(button.dataset.index), button);
  });

  $('.dm-close').addEventListener('click', close);
  $('.dm-prev').addEventListener('click', () => step(-1));
  $('.dm-next').addEventListener('click', () => step(1));
  $('.dm-play').addEventListener('click', () => (timer ? pause() : play()));
  modal.addEventListener('click', (event) => { if (event.target === modal) close(); });

  document.addEventListener('keydown', (event) => {
    if (modal.hidden) return;
    if (event.key === 'Escape') { event.preventDefault(); close(); return; }
    if (event.key === 'ArrowRight') { pause(); step(1); return; }
    if (event.key === 'ArrowLeft') { pause(); step(-1); return; }
    if (event.key === ' ') {
      // A focused button handles its own Space natively.
      if (document.activeElement && document.activeElement.tagName === 'BUTTON') return;
      event.preventDefault(); timer ? pause() : play(); return;
    }
    if (event.key !== 'Tab') return;
    // Focus trap: keep Tab inside the dialog.
    const focusable = [...modal.querySelectorAll('button')].filter((el) => !el.disabled);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    // Focus has left the dialog (e.g. a click on non-focusable text): pull it back.
    if (!modal.contains(document.activeElement)) { event.preventDefault(); first.focus(); return; }
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    // Capture phase: this must run before chrome.js's bubble-phase Escape
    // handler, so its defaultPrevented guard can see the modal claimed the key.
  }, true);

  // The filters stay live behind the modal. donors.js repaints first (target
  // phase), then this bubbles to document and re-reads the visible set.
  const refresh = () => { if (!modal.hidden) step(0); };
  document.addEventListener('input', refresh);
  document.addEventListener('change', refresh);
}
