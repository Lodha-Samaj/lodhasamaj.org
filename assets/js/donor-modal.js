import { displayNameParts, formatItems, donorTypes, typeLabel, initialOf } from './donors-core.js';
import { historyLinks, idFromHistoryHref, historyUrl } from './history-core.js';
import { historyHtml } from './history-view.js';
import { createHistoryLoader } from './history-fetch.js';

const AUTOPLAY_MS = 10000;

/** Pure: wrap an index, tolerating a stale index after the filter changed. */
export function nextIndex(current, delta, length) {
  if (length <= 0) return 0;
  if (current >= length) return delta > 0 ? 0 : length - 1;
  return (current + delta + length) % length;
}

/** True when the browser would simply follow a link: no modifier, left button.
 *  Ctrl/⌘/Shift/Alt and middle clicks stay the browser's, so the history page
 *  still opens in a new tab from inside the pop-up. */
export function isPlainClick(event) {
  return event.button === 0
    && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const LABELS = {
  hi: { close: 'बंद करें', prev: 'पिछला', next: 'अगला', play: 'चलाएँ', pause: 'रोकें', of: 'में से',
        back: 'दानदाता पर वापस', loading: 'दान इतिहास लोड हो रहा है…',
        notFound: 'यह दानदाता क्रमांक नहीं मिला', error: 'दान इतिहास लोड नहीं हो सका',
        openPage: 'पूरे पृष्ठ पर खोलें' },
  en: { close: 'Close', prev: 'Previous', next: 'Next', play: 'Play', pause: 'Pause', of: 'of',
        back: 'Back to the donor', loading: 'Loading the donation history…',
        notFound: 'This Donor ID was not found', error: 'The donation history could not be loaded',
        openPage: 'Open the full page' },
};

export function initModal(grid, getVisible, lang, year, getRegister = () => null,
                          loadHistory = createHistoryLoader()) {
  const T = LABELS[lang];
  let index = 0;
  let timer = null;
  let lastFocused = null;
  // 'donor' shows the slide, 'history' shows one person's whole giving.
  let mode = 'donor';
  // A slow fetch must not paint over a view the reader has already left.
  let pending = 0;

  const modal = document.createElement('div');
  modal.className = 'donor-modal';
  modal.hidden = true;
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'dm-name');
  modal.innerHTML = `
    <div class="donor-modal-box">
      <button class="dm-back" aria-label="${esc(T.back)}" hidden>❮ ${esc(T.back)}</button>
      <button class="dm-close" aria-label="${esc(T.close)}">×</button>
      <div class="dm-slide">
        <p class="dm-counter"></p>
        <div class="dm-progress"><div class="dm-bar"></div></div>
        <div class="dm-avatar"></div>
        <h2 class="dm-name" id="dm-name" tabindex="-1"></h2>
        <p class="dm-type"></p>
        <p class="dm-items"></p>
        <p class="dm-history"></p>
        <div class="dm-controls">
          <button class="dm-prev" aria-label="${esc(T.prev)}">❮</button>
          <button class="dm-play" aria-label="${esc(T.play)}">►</button>
          <button class="dm-next" aria-label="${esc(T.next)}">❯</button>
        </div>
      </div>
      <div class="dm-history-view" hidden></div>
    </div>`;
  document.body.appendChild(modal);

  const $ = (sel) => modal.querySelector(sel);
  const bar = $('.dm-bar');
  const slide = $('.dm-slide');
  const view = $('.dm-history-view');
  const back = $('.dm-back');

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
    $('.dm-history').replaceChildren(...historyLinks(donor, getRegister(), lang).map(({ id, href, text }) => {
      const link = document.createElement('a');
      link.setAttribute('href', href);
      link.dataset.id = id;
      link.textContent = text;
      return link;
    }));
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

  // The way out when the history itself cannot be shown: the real page.
  const fallback = (message, id) => `<div class="load-error">
      <p><strong>${esc(message)}</strong></p>
      <p><a href="${esc(historyUrl(id, lang))}" data-out="1">${esc(T.openPage)} →</a></p>
    </div>`;

  // A history taller than the box must say so: nothing else tells the reader
  // there is more below the fold.
  function markScrollable() {
    view.classList.toggle('is-scrollable',
      view.scrollHeight - view.scrollTop - view.clientHeight > 8);
  }
  view.addEventListener('scroll', markScrollable);

  async function openHistory(id) {
    pause();                          // the slideshow must not run on behind it
    mode = 'history';
    slide.hidden = true;
    back.hidden = false;
    view.hidden = false;
    view.innerHTML = `<p class="dm-loading">${esc(T.loading)}</p>`;
    view.scrollTop = 0;
    modal.setAttribute('aria-labelledby', 'dm-history-name');
    const token = ++pending;
    // Stale once the reader went back, closed, or asked for another person.
    const stale = () => token !== pending || mode !== 'history' || modal.hidden;
    try {
      const history = await loadHistory(id);
      if (stale()) return;
      view.innerHTML = history
        ? historyHtml(history, lang, { heading: 'h2', headingId: 'dm-history-name' })
        : fallback(T.notFound, id);
    } catch (error) {
      console.error(error);
      if (stale()) return;
      view.innerHTML = fallback(T.error, id);
    }
    view.scrollTop = 0;
    markScrollable();
    (view.querySelector('#dm-history-name') || back).focus();
  }

  function showDonor() {
    pending++;                        // a fetch still in flight is now stale
    mode = 'donor';
    view.hidden = true;
    view.replaceChildren();
    back.hidden = true;
    slide.hidden = false;
    modal.setAttribute('aria-labelledby', 'dm-name');
  }

  function backToDonor() {
    showDonor();
    show();
    $('.dm-name').focus();
  }

  function open(i, origin) {
    lastFocused = origin;
    index = i;
    showDonor();                      // a pop-up always opens on the donor
    modal.hidden = false;
    show();
    $('.dm-name').focus();            // move focus into the dialog
  }

  function close() {
    pause();
    showDonor();
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
  $('.dm-back').addEventListener('click', backToDonor);
  $('.dm-prev').addEventListener('click', () => step(-1));
  $('.dm-next').addEventListener('click', () => step(1));
  $('.dm-play').addEventListener('click', () => (timer ? pause() : play()));

  modal.addEventListener('click', (event) => {
    if (event.target === modal) { close(); return; }
    // Any link to a history - the donor's own, or a joint partner's inside the
    // history - opens here instead of navigating. data-out marks the one link
    // that must leave: the way to the real page when this view failed.
    const link = event.target.closest('a[href]');
    if (!link || link.dataset.out || !isPlainClick(event)) return;
    const id = link.dataset.id || idFromHistoryHref(link.getAttribute('href'));
    if (!id) return;
    event.preventDefault();
    openHistory(id);
  });

  document.addEventListener('keydown', (event) => {
    if (modal.hidden) return;
    // Escape steps back out of the history first, and only then closes.
    if (event.key === 'Escape') {
      event.preventDefault();
      mode === 'history' ? backToDonor() : close();
      return;
    }
    // The slideshow keys belong to the slide; in the history they would move a
    // donor the reader cannot see. Tab is not one of them - the focus trap
    // below must run in both views.
    if (mode === 'donor') {
      if (event.key === 'ArrowRight') { pause(); step(1); return; }
      if (event.key === 'ArrowLeft') { pause(); step(-1); return; }
      if (event.key === ' ') {
        // A focused button handles its own Space natively.
        if (document.activeElement && document.activeElement.tagName === 'BUTTON') return;
        event.preventDefault(); timer ? pause() : play(); return;
      }
    }
    if (event.key !== 'Tab') return;
    // Focus trap: keep Tab inside the dialog.
    // Links too: the history links must be reachable by keyboard.
    const focusable = [...modal.querySelectorAll('button, a[href]')]
      .filter((el) => !el.disabled && !el.closest('[hidden]'));
    if (!focusable.length) return;
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
  const refresh = () => { if (!modal.hidden && mode === 'donor') step(0); };
  document.addEventListener('input', refresh);
  document.addEventListener('change', refresh);
}
