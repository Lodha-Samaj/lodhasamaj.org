// Pure donor-history markup: one gatherHistory() object in, HTML out.
// No DOM, no fetch. The /daata/ page and the donor pop-up both render from
// here, so the two can never drift apart.

import { formatItems, formatTotal, typeLabel, displayName } from './donors-core.js';
import { listPageUrl, partnerNote, historyUrl } from './history-core.js';

// A year's list belongs to the नवदुर्गा महोत्सव, and in a history it is read
// beside the कावड़ यात्रा's own lists: "2025 दानदाता सूची" named no आयोजन, so two
// years in a row read as one repeated line. The festival's name is the same one
// the breadcrumb and FESTIVAL_SLUG use.
const LABELS = {
  hi: { idLabel: 'दानदाता क्रमांक', other: 'सूचियों में अन्य नाम', asListed: 'इस सूची में',
        jointTotals: 'संयुक्त दान सहित', yearTitle: (y) => `नवदुर्गा महोत्सव ${y}`, title: 'दान इतिहास',
        // दान counts alike either way; सूची does not.
        count: (gifts, lists) => `${gifts} दान · ${lists} ${lists === 1 ? 'सूची' : 'सूचियाँ'}` },
  en: { idLabel: 'Donor ID', other: 'Also listed as', asListed: 'As listed',
        jointTotals: 'including joint gifts', yearTitle: (y) => `Navdurga Mahotsav ${y}`, title: 'Donation history',
        count: (gifts, lists) =>
          `${gifts} ${gifts === 1 ? 'gift' : 'gifts'} · ${lists} ${lists === 1 ? 'list' : 'lists'}` },
};

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// On the English page, a Hindi-only name is marked lang="hi".
const nameSpan = (text, hasEn, lang) =>
  (lang === 'en' && !hasEn ? `<span lang="hi">${esc(text)}</span>` : esc(text));
const pick = (name, lang) => (name && (name[lang] || name.hi)) || '';

function groupTitle(list, lang) {
  return list.kind === 'year' ? LABELS[lang].yearTitle(list.year) : pick(list.data?.title, lang) || list.key;
}

// `heading` is the name already shown at the top. A gift printed under exactly
// that name says nothing new, so it goes unnamed; any other spelling is named,
// because it is how that list printed this donor.
function giftHtml({ entry, partners }, lang, heading) {
  const printed = displayName(entry, lang);
  const links = partners.map((p) =>
    `<a href="${historyUrl(p.id, lang)}">${nameSpan(pick(p.name, lang), p.name.en, lang)}</a>`);
  // partnerNote owns the wording; give it placeholders and swap the links in.
  const note = links.length
    ? `<p class="gift-joint">${esc(partnerNote(links.map((_, i) => `@@${i}@@`), lang))
        .replace(/@@(\d+)@@/g, (_, i) => links[i])}</p>`
    : '';
  const named = printed && printed !== heading
    ? `<p class="gift-name">${esc(LABELS[lang].asListed)}: ${nameSpan(printed, entry.name?.en, lang)}</p>`
    : '';
  return `<li class="gift">
      <p class="gift-items">${esc(formatItems(entry, lang))}</p>
      ${named}
      ${note}
    </li>`;
}

/** The whole history. `heading`/`headingId`: the pop-up labels its dialog with
 *  an <h2> it can focus; the page keeps its <h1>. */
export function historyHtml(h, lang, { heading = 'h1', headingId = '' } = {}) {
  const T = LABELS[lang];
  const attrs = headingId ? ` id="${esc(headingId)}" tabindex="-1"` : '';
  const sub = heading === 'h1' ? 'h2' : 'h3';   // group headings sit one level under the name
  const others = h.aliases.filter((a) => a !== h.name.hi);
  const totalsRow = h.totals.length
    ? `<div class="totals">${h.totals.map((row) =>
        `<p class="total"><b>${esc(formatTotal(row, lang))}</b><span>${esc(typeLabel(row.type, lang))}</span></p>`).join('')}</div>
       <p class="totals-note">${esc(T.jointTotals)}</p>`
    : '';
  return `
    <div class="section-head"><${heading}${attrs}>${nameSpan(pick(h.name, lang), h.name.en, lang)}</${heading}></div>
    <p class="donor-id">${esc(T.idLabel)} <b>${esc(h.id)}</b></p>
    ${others.length ? `<p class="donor-aliases">${esc(T.other)}: ${others.map((a) => nameSpan(a, false, lang)).join(' · ')}</p>` : ''}
    <p class="subtitle">${esc(T.count(h.count, h.listCount))}</p>
    ${totalsRow}
    ${h.groups.map((g) => `
      <section class="history-group">
        <${sub}><a href="${listPageUrl(g.list, lang)}">${esc(groupTitle(g.list, lang))}</a></${sub}>
        <ul class="gift-list">${g.entries.map((e) => giftHtml(e, lang, pick(h.name, lang))).join('')}</ul>
      </section>`).join('')}`;
}

export function historyDocTitle(h, lang) {
  return `${pick(h.name, lang)} — ${LABELS[lang].title}`;
}
