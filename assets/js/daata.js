import { formatItems, formatTotal, typeLabel, displayName } from './donors-core.js';
import {
  normalizeIdParam, resolveId, listOrder, listDataUrl, listPageUrl, gatherHistory, partnerNote, historyUrl,
} from './history-core.js';

const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'hi';
const root = document.getElementById('history-root');

const T = {
  hi: { idLabel: 'दानदाता क्रमांक', other: 'सूचियों में अन्य नाम', gifts: 'दान', lists: 'सूचियाँ',
        jointTotals: 'संयुक्त दान सहित', yearTitle: (y) => `${y} दानदाता सूची`, title: 'दान इतिहास',
        notFound: 'यह दानदाता क्रमांक नहीं मिला', back: 'दान पृष्ठ पर जाएँ', error: 'दान इतिहास लोड नहीं हो सका' },
  en: { idLabel: 'Donor ID', other: 'Also listed as', gifts: 'gifts', lists: 'lists',
        jointTotals: 'including joint gifts', yearTitle: (y) => `${y} Donor List`, title: 'Donation history',
        notFound: 'This Donor ID was not found', back: 'Go to the Donate page', error: 'The donation history could not be loaded' },
}[lang];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// On the English page, a Hindi-only name is marked lang="hi".
const nameSpan = (text, hasEn) => (lang === 'en' && !hasEn ? `<span lang="hi">${esc(text)}</span>` : esc(text));
const pick = (name) => (name && (name[lang] || name.hi)) || '';

async function getJSON(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  return response.json();
}

function groupTitle(list) {
  return list.kind === 'year' ? T.yearTitle(list.year) : pick(list.data?.title) || list.key;
}

function giftHtml({ entry, partners }) {
  const printed = displayName(entry, lang);
  const links = partners.map((p) =>
    `<a href="${historyUrl(p.id, lang)}">${nameSpan(pick(p.name), p.name.en)}</a>`);
  // partnerNote owns the wording; give it placeholders and swap the links in.
  const note = links.length
    ? `<p class="gift-joint">${esc(partnerNote(links.map((_, i) => `@@${i}@@`), lang))
        .replace(/@@(\d+)@@/g, (_, i) => links[i])}</p>`
    : '';
  return `<li class="gift">
      <p class="gift-items">${esc(formatItems(entry, lang))}</p>
      <p class="gift-name">${nameSpan(printed, entry.name?.en)}</p>
      ${note}
    </li>`;
}

function render(h) {
  const others = h.aliases.filter((a) => a !== h.name.hi);
  const totalsRow = h.totals.length
    ? `<div class="totals">${h.totals.map((row) =>
        `<p class="total"><b>${esc(formatTotal(row, lang))}</b><span>${esc(typeLabel(row.type, lang))}</span></p>`).join('')}</div>
       <p class="totals-note">${esc(T.jointTotals)}</p>`
    : '';
  root.innerHTML = `
    <div class="section-head"><h1>${nameSpan(pick(h.name), h.name.en)}</h1></div>
    <p class="donor-id">${esc(T.idLabel)} <b>${esc(h.id)}</b></p>
    ${others.length ? `<p class="donor-aliases">${esc(T.other)}: ${others.map((a) => nameSpan(a, false)).join(' · ')}</p>` : ''}
    <p class="subtitle">${h.count} ${esc(T.gifts)} · ${h.listCount} ${esc(T.lists)}</p>
    ${totalsRow}
    ${h.groups.map((g) => `
      <section class="history-group">
        <h2><a href="${listPageUrl(g.list, lang)}">${esc(groupTitle(g.list))}</a></h2>
        <ul class="gift-list">${g.entries.map(giftHtml).join('')}</ul>
      </section>`).join('')}`;
  document.title = `${pick(h.name)} — ${T.title}`;
}

function message(text) {
  root.innerHTML = `<div class="load-error"><p><strong>${esc(text)}</strong></p>
    <p><a href="/${lang}/daan/">${esc(T.back)} →</a></p></div>`;
}

async function main() {
  const raw = new URLSearchParams(location.search).get('id');
  const [register, index] = await Promise.all([getJSON('/data/donors.json'), getJSON('/data/donors-index.json')]);
  const id = resolveId(register, normalizeIdParam(raw));
  if (!id) { message(T.notFound); return; }
  const order = listOrder(index);
  const datas = await Promise.all(order.map((list) => getJSON(listDataUrl(list))));
  const found = gatherHistory(register, order.map((list, i) => ({ ...list, data: datas[i] })), id);
  // A merged, lower-case or padded ID moves the address to the kept ID, so a
  // shared link always shows the canonical one.
  if (found.id !== raw) window.history.replaceState(null, '', `?id=${found.id}`);
  keepIdOnLanguageToggle(found.id);
  render(found);
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
