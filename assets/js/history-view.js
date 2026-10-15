// Pure donor-history markup: one gatherHistory() object in, HTML out.
// No DOM, no fetch. The /daata/ page and the donor pop-up both render from
// here, so the two can never drift apart.

import { formatItems, formatTotal, typeLabel, displayName } from './donors-core.js';
import { listPageUrl, partnerNote, historyUrl } from './history-core.js';

const LABELS = {
  hi: { idLabel: 'दानदाता क्रमांक', other: 'सूचियों में अन्य नाम', gifts: 'दान', lists: 'सूचियाँ',
        jointTotals: 'संयुक्त दान सहित', yearTitle: (y) => `${y} दानदाता सूची`, title: 'दान इतिहास' },
  en: { idLabel: 'Donor ID', other: 'Also listed as', gifts: 'gifts', lists: 'lists',
        jointTotals: 'including joint gifts', yearTitle: (y) => `${y} Donor List`, title: 'Donation history' },
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

function giftHtml({ entry, partners }, lang) {
  const printed = displayName(entry, lang);
  const links = partners.map((p) =>
    `<a href="${historyUrl(p.id, lang)}">${nameSpan(pick(p.name, lang), p.name.en, lang)}</a>`);
  // partnerNote owns the wording; give it placeholders and swap the links in.
  const note = links.length
    ? `<p class="gift-joint">${esc(partnerNote(links.map((_, i) => `@@${i}@@`), lang))
        .replace(/@@(\d+)@@/g, (_, i) => links[i])}</p>`
    : '';
  return `<li class="gift">
      <p class="gift-items">${esc(formatItems(entry, lang))}</p>
      <p class="gift-name">${nameSpan(printed, entry.name?.en, lang)}</p>
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
    <p class="subtitle">${h.count} ${esc(T.gifts)} · ${h.listCount} ${esc(T.lists)}</p>
    ${totalsRow}
    ${h.groups.map((g) => `
      <section class="history-group">
        <${sub}><a href="${listPageUrl(g.list, lang)}">${esc(groupTitle(g.list, lang))}</a></${sub}>
        <ul class="gift-list">${g.entries.map((e) => giftHtml(e, lang)).join('')}</ul>
      </section>`).join('')}`;
}

export function historyDocTitle(h, lang) {
  return `${pick(h.name, lang)} — ${LABELS[lang].title}`;
}
