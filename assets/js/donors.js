import {
  typeLabel, displayName, displayNameParts, formatItems, formatTotal, festivalHeading, donorTypes, matchesType, matchesQuery,
  presentTypes, totals, sortDonors, initialOf, listSource,
} from './donors-core.js';

import { initModal } from './donor-modal.js';

const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'hi';
const year = document.body.dataset.year;
// A named list (data-list) carries its own title; a year page builds one.
const source = listSource(document.body.dataset);
const root = document.getElementById('donor-root');
let visible = [];

const T = {
  hi: { search: 'दानदाता खोजें…', allTypes: 'सभी प्रकार', typeBy: 'प्रकार से छाँटें', sortBy: 'क्रम',
        byName: 'नाम से', byType: 'प्रकार से', none: 'कोई परिणाम नहीं मिला', count: (n) => `${n} परिणाम`,
        error: 'सूची लोड नहीं हो सकी', empty: 'इस वर्ष की सूची जल्द ही यहाँ प्रकाशित होगी।', archive: 'सभी वर्ष देखें',
        donors: 'दानदाता', title: (y) => `${y} दानदाता सूची`,
        back: 'दान पृष्ठ', listEmpty: 'सूची जल्द ही यहाँ प्रकाशित होगी।' },
  en: { search: 'Search donors…', allTypes: 'All types', typeBy: 'Filter by type', sortBy: 'Sort donors',
        byName: 'By name', byType: 'By type', none: 'No results found', count: (n) => `${n} results`,
        error: 'The list could not be loaded', empty: 'This year\'s list will be published here soon.', archive: 'View all years',
        donors: 'donors', title: (y) => `${y} Donor List`,
        back: 'Donate page', listEmpty: 'The list will be published here soon.' },
}[lang];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function nameHtml(donor) {
  const { prefix, name, hindi } = displayNameParts(donor, lang);
  const body = hindi ? `<span lang="hi">${esc(name)}</span>` : esc(name);
  return prefix ? `${esc(prefix)} ${body}` : body;
}

function totalsHtml(donors) {
  const rows = totals(donors);
  if (!rows.length) return '';      // an empty .stats box looks broken
  return `<div class="totals">${rows.map((row) =>
    `<p class="total"><b>${esc(formatTotal(row, lang))}</b><span>${esc(typeLabel(row.type, lang))}</span></p>`
  ).join('')}</div>`;
}

function cardHtml(donor, index) {
  // No type tag on the row: formatItems already names every type it would list
  // ("501 किलो शक्कर", "101 किलो आटा + ₹1,100 नगद"). Verified against all 82
  // donors in both languages. The type filter reads the donor data, not the DOM.
  const photo = donor.photo
    ? `<img class="avatar" src="${esc(donor.photo)}" alt="" width="44" height="44">`
    : `<span class="avatar avatar-initial" aria-hidden="true">${esc(initialOf(donor))}</span>`;
  return `<article class="donor-card${donor.memoriam ? ' memoriam' : ''}">
    ${photo}
    <h3>${nameHtml(donor)}</h3>
    <p>${esc(formatItems(donor, lang))}</p>
    <button class="donor-open" data-index="${index}"
            aria-label="${esc(displayName(donor, lang))}"></button>
  </article>`;
}

function render(data) {
  const { donors } = data;
  const named = source.named;
  const title = named ? (data.title?.[lang] || data.title?.hi || '') : T.title(year);
  const backText = named ? T.back : T.archive;
  const subtitle = [named ? (data.subtitle?.[lang] || '') : festivalHeading(data.festival, lang),
                    donors.length ? `${donors.length} ${donors.length === 1 && lang === 'en' ? 'donor' : T.donors}` : '']
    .filter(Boolean).join(' · ');
  if (!donors.length) {
    // The first week of a new year: say so, rather than show empty widgets
    // and "no results found", which reads like a bug.
    root.innerHTML = `
    <div class="section-head">
      <h1>${esc(title)}</h1>
      <a class="all" href="/${lang}/daan/">${esc(backText)}</a>
    </div>
    ${subtitle ? `<p class="subtitle">${esc(subtitle)}</p>` : ''}
    <p class="no-results" role="status">${esc(named ? T.listEmpty : T.empty)}</p>`;
    return;
  }
  root.innerHTML = `
    <div class="section-head">
      <h1>${esc(title)}</h1>
      <a class="all" href="/${lang}/daan/">${esc(backText)}</a>
    </div>
    ${subtitle ? `<p class="subtitle">${esc(subtitle)}</p>` : ''}
    ${totalsHtml(donors)}
    <div class="filters">
      <input id="q" type="search" placeholder="${esc(T.search)}" aria-label="${esc(T.search)}">
      <select id="type" aria-label="${esc(T.typeBy)}">
        <option value="">${esc(T.allTypes)}</option>
        ${presentTypes(donors).map((c) =>
          `<option value="${esc(c)}">${esc(typeLabel(c, lang))}</option>`).join('')}
      </select>
      <select id="sort" aria-label="${esc(T.sortBy)}">
        <option value="">${esc(T.sortBy)}</option>
        <option value="name">${esc(T.byName)}</option>
        <option value="type">${esc(T.byType)}</option>
      </select>
    </div>
    <div class="donor-roll" id="grid"></div>
    <p class="no-results" id="none" role="status"></p>`;

  const [q, type, sort, grid, none] =
    ['q', 'type', 'sort', 'grid', 'none'].map((id) => document.getElementById(id));

  function paint() {
    const shown = sortDonors(donors, sort.value, lang)
      .filter((d) => matchesType(d, type.value) && matchesQuery(d, q.value, lang));
    grid.innerHTML = shown.map(cardHtml).join('');
    none.textContent = shown.length ? T.count(shown.length) : T.none;
    // Task 6A's modal cycles the *visible* set, so it reads this.
    visible = shown;
  }

  [q, type, sort].forEach((el) => el.addEventListener('input', paint));
  paint();
  initModal(grid, () => visible, lang, named ? '' : year);
}

Promise.resolve(source)
  .then((src) => {
    if (!src) throw new Error('page has no valid data-year or data-list');
    return fetch(src.url, { cache: 'no-cache' });
  })
  .then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(render)
  .catch((error) => {
    // A trailing comma in the JSON lands here. Never leave a blank page.
    console.error(error);
    root.innerHTML = `<div class="load-error">
      <p><strong>${esc(T.error)}</strong></p>
      <p><a href="/${lang}/daan/">${esc(source?.named ? T.back : T.archive)} →</a></p></div>`;
  });
