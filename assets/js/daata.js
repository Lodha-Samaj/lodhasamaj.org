import { normalizeIdParam } from './history-core.js';
import { historyHtml, historyDocTitle } from './history-view.js';
import { createHistoryLoader } from './history-fetch.js';

const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'hi';
const root = document.getElementById('history-root');

const T = {
  hi: { notFound: 'यह दानदाता क्रमांक नहीं मिला', back: 'दान पृष्ठ पर जाएँ',
        error: 'दान इतिहास लोड नहीं हो सका' },
  en: { notFound: 'This Donor ID was not found', back: 'Go to the Donate page',
        error: 'The donation history could not be loaded' },
}[lang];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function message(text) {
  root.innerHTML = `<div class="load-error"><p><strong>${esc(text)}</strong></p>
    <p><a href="/${lang}/daan/">${esc(T.back)} →</a></p></div>`;
}

async function main() {
  const raw = new URLSearchParams(location.search).get('id');
  const history = createHistoryLoader();
  const found = await history(normalizeIdParam(raw));
  if (!found) { message(T.notFound); return; }
  // A merged, lower-case or padded ID moves the address to the kept ID, so a
  // shared link always shows the canonical one.
  if (found.id !== raw) window.history.replaceState(null, '', `?id=${found.id}`);
  keepIdOnLanguageToggle(found.id);
  root.innerHTML = historyHtml(found, lang);
  document.title = historyDocTitle(found, lang);
}

// chrome.js builds the EN/हि toggle from the hreflang link, which has no ?id=.
function keepIdOnLanguageToggle(id) {
  const toggle = document.querySelector('.lang-toggle');
  if (toggle) toggle.setAttribute('href', `${toggle.getAttribute('href').split('?')[0]}?id=${id}`);
}

main().catch((error) => {
  console.error(error);
  message(T.error);
});
