// Pure donor-list logic. No DOM, no fetch — so it is testable with node:test.

export const TYPE_LABELS = {
  sugar:   { hi: 'शक्कर',           en: 'Sugar' },
  flour:   { hi: 'आटा',             en: 'Flour' },
  oil:     { hi: 'तेल',             en: 'Oil' },
  salt:    { hi: 'नमक',             en: 'Salt' },
  ghee:    { hi: 'घी',              en: 'Ghee' },
  mawa:    { hi: 'मावा',            en: 'Mawa' },
  cash:    { hi: 'नगद',             en: 'Cash' },
  water:   { hi: 'पानी',            en: 'Water' },
  gas:     { hi: 'गैस टंकी',        en: 'Gas cylinder' },
  coconut: { hi: 'नारियल',          en: 'Coconut' },
  pattal:  { hi: 'केले के पत्तल',   en: 'Banana-leaf plates' },
  besan:   { hi: 'बेसन',            en: 'Besan' },
  rava:    { hi: 'रवा',             en: 'Rava (semolina)' },
  rice:    { hi: 'चावल',            en: 'Rice' },
  dal:     { hi: 'दाल',             en: 'Dal' },
  vegetables: { hi: 'हरी सब्जियाँ', en: 'Vegetables' },
  falahar: { hi: 'फलाहार',          en: 'Falahar (fruit fare)' },
  sweets:  { hi: 'मिठाई',           en: 'Sweets' },
  // कावड़ यात्रा: someone paid for a whole arrangement at one stop rather than
  // handing over goods. No quantity - the `note` says where.
  lodging: { hi: 'धर्मशाला व्यवस्था', en: 'Lodging arranged' },
  meals:   { hi: 'भोजन व्यवस्था',   en: 'Meals arranged' },
  vehicle: { hi: 'वाहन व्यवस्था',   en: 'Vehicle arranged' },
  // श्री हनुमान मंदिर निर्माण: building materials, not भंडारा supplies.
  cement:  { hi: 'सीमेंट',          en: 'Cement' },
  brick:   { hi: 'ईंट',             en: 'Bricks' },
  rebar:   { hi: 'सरिया',           en: 'Steel rods (sariya)' },
  tiles:   { hi: 'टाइल्स',          en: 'Tiles' },
  fan:     { hi: 'छत का पंखा',      en: 'Ceiling fan' },
  other:   { hi: 'अन्य',            en: 'Other' },
};

export const UNIT_LABELS = {
  kg:       { hi: 'किलो',  en: 'kg' },
  tin:      { hi: 'डब्बा', en: 'tin',   enPlural: 'tins' },
  inr:      { hi: '',      en: '' },      // the ₹ sign carries it
  jar:      { hi: 'जार',   en: 'jar',   enPlural: 'jars' },
  // The type label ("Gas cylinder") already says it; "7 cylinder Gas cylinder"
  // would stutter. Hindi `छोटी` is an adjective that reads fine before गैस टंकी.
  cylinder: { hi: 'छोटी',  en: '' },
  piece:    { hi: 'नग',    en: 'piece', enPlural: 'pieces' },
  bag:      { hi: 'बोरी',  en: 'bag',   enPlural: 'bags' },
  // A bare count: "551 ईंट", "551 Bricks" - the type label names the thing.
  count:    { hi: '',      en: '' },
};

const CURRENCY_UNIT = 'inr';
const MEMORIAM_PREFIX = { hi: 'स्व.', en: 'Late' };

/** Where a donor page's data lives: `data-year="2025"` for a नवरात्र year, or
 *  `data-list="hanuman-mandir"` for a named list such as a building campaign.
 *  The value becomes part of a URL, so only a plain slug is accepted; anything
 *  else returns null and the page shows its load error. */
export function listSource(dataset) {
  if ('list' in dataset) {
    return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(dataset.list)
      ? { url: `/data/${dataset.list}.json`, named: true } : null;
  }
  return /^\d{4}$/.test(dataset.year ?? '')
    ? { url: `/data/donors-${dataset.year}.json`, named: false } : null;
}

/** Unit text for `qty` ("1 tin", "2 tins"); unknown units are returned as-is. */
export function unitLabel(unit, lang, qty) {
  const u = UNIT_LABELS[unit];
  if (!u) return unit ?? '';
  if (lang === 'en' && u.enPlural && qty !== 1) return u.enPlural;
  return u[lang];
}

/** Unknown codes are returned as-is so a typo is visible, not swallowed. */
export function typeLabel(code, lang) {
  return TYPE_LABELS[code] ? TYPE_LABELS[code][lang] : code;
}

/** NFC, strip zero-width joiners, fold case, collapse whitespace. */
export function normalize(text) {
  return String(text ?? '')
    .normalize('NFC')
    .replace(/[‌‍]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

export function displayName(donor, lang) {
  const base = (donor.name && (donor.name[lang] || donor.name.hi)) || '';
  return donor.memoriam ? `${MEMORIAM_PREFIX[lang]} ${base}` : base;
}

/** True when `lang` is English but the name shown is the Hindi one, so the
 *  page should mark it lang="hi" (screen readers, font selection). */
export function nameIsHindiOnly(donor, lang) {
  return lang === 'en' && !donor.name?.en;
}

/** displayName split so a caller can mark only the name's language:
 *  { prefix: 'Late' | 'स्व.' | '', name, hindi }. */
export function displayNameParts(donor, lang) {
  const name = (donor.name && (donor.name[lang] || donor.name.hi)) || '';
  return { prefix: donor.memoriam ? MEMORIAM_PREFIX[lang] : '', name,
           hindi: nameIsHindiOnly(donor, lang) };
}

/** Unique type codes for a donor; anything outside the vocabulary becomes `other`. */
export function donorTypes(donor) {
  const seen = [];
  for (const item of donor.items || []) {
    const code = TYPE_LABELS[item.type] ? item.type : 'other';
    if (!seen.includes(code)) seen.push(code);
  }
  return seen;
}

export function matchesType(donor, code) {
  return !code || donorTypes(donor).includes(code);
}

export function matchesQuery(donor, query, lang) {
  const needle = normalize(query);
  if (!needle) return true;
  const haystack = normalize(
    `${donor.name?.hi ?? ''} ${donor.name?.en ?? ''} ${displayName(donor, lang)}`,
  );
  return haystack.includes(needle);
}

export function presentTypes(donors) {
  const seen = [];
  for (const donor of donors) {
    for (const code of donorTypes(donor)) if (!seen.includes(code)) seen.push(code);
  }
  return seen;
}

/** Sums by (type, unit), skipping anything non-numeric. Never returns NaN. */
export function totals(donors) {
  const sums = new Map();
  for (const donor of donors) {
    for (const item of donor.items || []) {
      if (!Number.isFinite(item.qty) || !item.unit) continue;
      const key = `${item.type}|${item.unit}`;
      sums.set(key, (sums.get(key) || 0) + item.qty);
    }
  }
  // Deliberate order: the TYPE_LABELS vocabulary. Quantities are never
  // compared across units; unknown types go last. Array sort is stable.
  const order = Object.keys(TYPE_LABELS);
  const rank = (type) => (order.includes(type) ? order.indexOf(type) : order.length);
  return [...sums.entries()]
    .map(([key, qty]) => {
      const [type, unit] = key.split('|');
      return { type, unit, qty };
    })
    .sort((a, b) => rank(a.type) - rank(b.type));
}

/** "1,923 किलो" or "₹1,50,900" for a totals row (the label is shown separately). */
export function formatTotal(row, lang) {
  const grouped = row.qty.toLocaleString('en-IN');
  if (row.unit === CURRENCY_UNIT) return `₹${grouped}`;
  const unit = unitLabel(row.unit, lang, row.qty);
  return `${grouped} ${unit}`.trim();
}

/** 1st, 2nd, 3rd, 4th ... 11th, 12th, 13th, 21st, 22nd, 23rd, 111th. */
export function ordinal(n) {
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 13) return `${n}th`;
  const suffix = { 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th';
  return `${n}${suffix}`;
}

/** "45वां विशाल भंडारा · 22वां नगर कन्या पूजन"; absent counts are skipped. */
export function festivalHeading(festival, lang) {
  const f = festival || {};
  const parts = lang === 'hi'
    ? [f.bhandara && `${f.bhandara}वां विशाल भंडारा`,
       f.kanyaPujan && `${f.kanyaPujan}वां नगर कन्या पूजन`]
    : [f.bhandara && `${ordinal(f.bhandara)} Vishal Bhandara`,
       f.kanyaPujan && `${ordinal(f.kanyaPujan)} Nagar Kanya Pujan`];
  return parts.filter(Boolean).join(' · ');
}

// Longest-first: regex alternation takes the first match, so `श्री`
// would otherwise shadow `श्रीमती`. The page marks death three ways
// (`स्वर्गीय`, `स्व.`, `स्व•`). Repeating group: a name can stack markers
// ("स्वर्गीय श्री ...", "पंडित श्री ..."), so one pass is not enough.
// Word-form markers need a boundary so श्रीकांत / श्रीराम keep their name;
// the punctuated forms (`स्व.`, `डॉ.`) carry their own boundary.
const HONORIFIC_PREFIX = {
  hi: /^(?:(?:(?:स्वर्गीय|श्रीमती|श्री|पंडित)(?=\s|$)|स्व\s*[.•]|डॉ\.)\s*)+/,
  en: /^(?:(?:Late|Shri|Smt|Dr|Pandit)(?=[\s.]|$)\.?\s*)+/i,
};

/** The name as displayed in `lang` (falling back to Hindi), honorifics removed. */
function givenName(donor, lang = 'hi') {
  const useEn = lang === 'en' && donor.name?.en;
  const raw = (useEn ? donor.name.en : donor.name?.hi) || '';
  return raw.replace(HONORIFIC_PREFIX[useEn ? 'en' : 'hi'], '').trim();
}

/** The list split into one block per kind of giving: `[{ type, label, donors }]`.
 *  Blocks come in the order the list itself introduces each type, so the
 *  समाज's own ordering survives; a donor who gave two things sits under the
 *  first of them (the row still prints both) and so appears exactly once. */
export function groupByType(donors, lang) {
  const blocks = new Map();
  for (const donor of donors) {
    // No type recorded is 'other' ("अन्य") - never a block with a blank heading.
    const code = donorTypes(donor)[0] || 'other';
    if (!blocks.has(code)) blocks.set(code, []);
    blocks.get(code).push(donor);
  }
  return [...blocks].map(([type, members]) =>
    ({ type, label: typeLabel(type, lang), donors: members }));
}

export function sortDonors(donors, by, lang) {
  const copy = [...donors];
  if (by === 'name') {
    // Collate by given name so the honorific does not cluster donors by title.
    const key = (donor) => (givenName(donor, lang) || displayName(donor, lang));
    copy.sort((a, b) => key(a).localeCompare(key(b), lang));
  } else if (by === 'type') {
    copy.sort((a, b) =>
      typeLabel(donorTypes(a)[0] ?? '', lang).localeCompare(
        typeLabel(donorTypes(b)[0] ?? '', lang), 'hi'));
  }
  return copy;
}

function formatOne(item, lang) {
  const label = typeLabel(item.type, lang);
  const unit = unitLabel(item.unit, lang, item.qty);
  let text;
  if (item.qty === undefined || item.qty === null) {
    text = label;
  } else if (!Number.isFinite(item.qty)) {
    // Present but not a finite number: show the value as entered, never drop it.
    text = `${item.qty} ${unit} ${label}`.replace(/\s+/g, ' ');
  } else if (item.unit === CURRENCY_UNIT) {
    text = `₹${item.qty.toLocaleString('en-IN')} ${label}`;
  } else {
    text = `${item.qty} ${unit} ${label}`.replace(/\s+/g, ' ');
  }
  const body = text.trim();
  if (!item.note) return body;
  return body ? `${body} (${item.note})` : item.note;
}

export function formatItems(donor, lang) {
  // Every gift names what it was, in the row as in the pop-up: a column of bare
  // quantities under a type heading leaves the reader counting nothing.
  return (donor.items || []).map((item) => formatOne(item, lang)).join(' + ');
}

/** First letter, for a typographic avatar. The 2025 page used one stock
 *  Pixabay icon for all 44 donors; an initial is more dignified. */
export function initialOf(donor) {
  const name = givenName(donor, 'hi');
  return name ? [...name][0] : '·';
}
