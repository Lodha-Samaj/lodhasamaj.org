import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  TYPE_LABELS, typeLabel, normalize, displayName, donorTypes, matchesType,
  matchesQuery, presentTypes, totals, formatTotal, nameIsHindiOnly, displayNameParts, ordinal, festivalHeading, sortDonors, formatItems, initialOf,
  listSource, groupByType,
} from './donors-core.js';

const d = (hi, items, extra = {}) => ({ name: { hi }, items, ...extra });

test('typeLabel returns the Hindi and English labels', () => {
  assert.equal(typeLabel('sugar', 'hi'), 'शक्कर');
  assert.equal(typeLabel('sugar', 'en'), 'Sugar');
});

test('typeLabel shows the raw code for an unknown type so a typo is visible', () => {
  assert.equal(typeLabel('sakkar', 'hi'), 'sakkar');
});

test('an unknown type is grouped under अन्य but keeps its raw label', () => {
  const donor = d('श्री क', [{ type: 'sakkar', qty: 5, unit: 'kg' }]);
  assert.deepEqual(donorTypes(donor), ['other']);
  assert.match(formatItems(donor, 'hi'), /sakkar/);
});

test('normalize makes NFD, NFC and ZWJ spellings compare equal', () => {
  const nfc = 'श्री';
  const nfd = nfc.normalize('NFD');
  assert.equal(normalize(nfd), normalize(nfc));
  assert.equal(normalize('क्‍क'), normalize('क्क'));
});

test('search matches a name typed in a different normalization', () => {
  const donor = d('श्री संजय जी जमदार', [{ type: 'sugar', qty: 501, unit: 'kg' }]);
  assert.ok(matchesQuery(donor, 'संजय'.normalize('NFD'), 'hi'));
  assert.ok(matchesQuery(donor, '  संजय  ', 'hi'));
  assert.ok(!matchesQuery(donor, 'रमेश', 'hi'));
});

test('an empty query matches every donor', () => {
  assert.ok(matchesQuery(d('श्री क', []), '', 'hi'));
});

test('a multi-type donor matches each of its types exactly once', () => {
  const donor = d('श्री राकेश जी चौधरी', [
    { type: 'flour', qty: 101, unit: 'kg' },
    { type: 'cash', qty: 1100, unit: 'inr' },
    { type: 'oil', qty: 4, unit: 'tin' },
  ]);
  assert.deepEqual(donorTypes(donor).sort(), ['cash', 'flour', 'oil']);
  for (const code of ['flour', 'cash', 'oil']) assert.ok(matchesType(donor, code));
  assert.ok(!matchesType(donor, 'sugar'));
  assert.equal(donorTypes(donor).filter((t) => t === 'flour').length, 1);
});

test('two items of the same type collapse in the type list but both count', () => {
  const donor = d('श्री ख', [
    { type: 'flour', qty: 51, unit: 'kg' },
    { type: 'flour', qty: 50, unit: 'kg' },
  ]);
  assert.deepEqual(donorTypes(donor), ['flour']);
  assert.deepEqual(totals([donor]), [{ type: 'flour', unit: 'kg', qty: 101 }]);
});

test('a donor with no qty is still listed but skipped in totals', () => {
  const donors = [
    d('श्री मनोहर जी वर्मा', [{ type: 'pattal', note: 'सम्पूर्ण भंडारे हेतु' }]),
    d('श्री ग', [{ type: 'sugar', qty: 51, unit: 'kg' }]),
  ];
  assert.deepEqual(presentTypes(donors).sort(), ['pattal', 'sugar']);
  assert.deepEqual(totals(donors), [{ type: 'sugar', unit: 'kg', qty: 51 }]);
});

test('a non-numeric qty never produces NaN in totals', () => {
  const donors = [d('श्री घ', [
    { type: 'sugar', qty: Number.NaN, unit: 'kg' },
    { type: 'sugar', qty: Number.POSITIVE_INFINITY, unit: 'kg' },
    { type: 'sugar', qty: null, unit: 'kg' },
    { type: 'sugar', qty: undefined, unit: 'kg' },
    { type: 'sugar', qty: '51', unit: 'kg' },
    { type: 'sugar', qty: 'इक्यावन', unit: 'kg' },
    { type: 'sugar', qty: 51, unit: 'kg' },
  ])];
  const rows = totals(donors);
  assert.ok(rows.length > 0, 'the valid row must survive, so the loop below runs');
  assert.deepEqual(rows, [{ type: 'sugar', unit: 'kg', qty: 51 }]);
  for (const row of rows) assert.ok(Number.isFinite(row.qty));
});

test('a non-numeric qty keeps its text, and a missing qty renders as type and note', () => {
  assert.equal(formatItems(d('x', [{ type: 'sugar', qty: 'इक्यावन', unit: 'kg' }]), 'hi'),
    'इक्यावन किलो शक्कर');
  assert.equal(formatItems(d('x', [{ type: 'pattal', note: 'सम्पूर्ण भंडारे हेतु' }]), 'hi'),
    'केले के पत्तल (सम्पूर्ण भंडारे हेतु)');
  assert.equal(formatItems(d('x', [{ type: 'coconut', note: 'कन्या पूजन हेतु संपूर्ण श्रीफल' }]), 'hi'),
    'नारियल (कन्या पूजन हेतु संपूर्ण श्रीफल)');
});

test('memoriam adds the prefix in each language', () => {
  const donor = d('श्रीमती आशा जी जाट', [], { memoriam: true });
  assert.equal(displayName(donor, 'hi'), 'स्व. श्रीमती आशा जी जाट');
  assert.equal(displayName(donor, 'en'), 'Late श्रीमती आशा जी जाट');
});

test('an English name is used when present and falls back to Hindi otherwise', () => {
  const withEn = { name: { hi: 'श्री क', en: 'Shri K' }, items: [] };
  assert.equal(displayName(withEn, 'en'), 'Shri K');
  assert.equal(displayName(d('श्री ख', []), 'en'), 'श्री ख');
});

test('presentTypes lists only types in the data, with no duplicates', () => {
  const donors = [
    d('a', [{ type: 'sugar', qty: 1, unit: 'kg' }]),
    d('b', [{ type: 'sugar', qty: 2, unit: 'kg' }, { type: 'salt', qty: 3, unit: 'kg' }]),
  ];
  assert.deepEqual(presentTypes(donors).sort(), ['salt', 'sugar']);
  assert.ok(!presentTypes(donors).includes('besan'));
});

test('sortDonors by name uses Hindi collation and does not mutate the input', () => {
  const donors = [d('श्री रमेश', []), d('श्री अजय', [])];
  const sorted = sortDonors(donors, 'name', 'hi');
  assert.equal(sorted[0].name.hi, 'श्री अजय');
  assert.equal(donors[0].name.hi, 'श्री रमेश');
});

test('sortDonors by name collates by given name, not by honorific', () => {
  const donors = [d('श्रीमती राजो बाई', []), d('डॉ. सेठिया', []), d('श्री अजय', [])];
  const sorted = sortDonors(donors, 'name', 'hi').map((x) => x.name.hi);
  assert.deepEqual(sorted, ['श्री अजय', 'श्रीमती राजो बाई', 'डॉ. सेठिया']);
});

test('formatItems renders quantity, unit and note', () => {
  assert.equal(formatItems(d('x', [{ type: 'sugar', qty: 501, unit: 'kg' }]), 'hi'),
    '501 किलो शक्कर');
  assert.equal(formatItems(d('x', [{ type: 'cash', qty: 7100, unit: 'inr' }]), 'hi'),
    '₹7,100 नगद');
  assert.match(formatItems(d('x', [{ type: 'ghee', qty: 1, unit: 'tin', note: 'शुद्ध देसी' }]), 'hi'),
    /शुद्ध देसी/);
});

test('the real 2025 file produces the hand-verified totals', () => {
  const data = JSON.parse(readFileSync(new URL('../../data/donors-2025.json', import.meta.url)));
  // Golden snapshot of the समाज's full 2025 सहयोगकर्ता सूची (166 entries,
  // against the 82 that were on the old website). Every figure below was
  // tallied twice from the markdown source by two independent routes before
  // being written down. tools/convert_2025_md.py regenerates the file.
  assert.equal(data.donors.length, 166);
  const find = (type, unit) => totals(data.donors).find((r) => r.type === type && r.unit === unit).qty;
  assert.equal(find('flour', 'kg'), 2650);
  assert.equal(find('sugar', 'kg'), 2978);
  assert.equal(find('cash', 'inr'), 233206);
  assert.equal(find('oil', 'tin'), 48);
  assert.equal(find('salt', 'kg'), 289);
  assert.equal(find('water', 'jar'), 152);
  assert.equal(find('mawa', 'kg'), 369);
  assert.equal(find('besan', 'kg'), 125);
  assert.equal(find('rava', 'kg'), 11);
  // One donor gave तेल by weight rather than by the tin, so oil reaches the
  // totals twice, under two units. REVIEW: the समाज should confirm #110.
  assert.equal(find('oil', 'kg'), 11);
  // 14 types appear in 2025; 13 reach totals. pattal, rice and one coconut
  // entry are stated as "the whole bhandara" with no quantity.
  assert.equal(presentTypes(data.donors).length, 14);
  assert.equal(totals(data.donors).length, 13);
  assert.ok(presentTypes(data.donors).includes('pattal'));
  assert.ok(presentTypes(data.donors).includes('rice'));
});

test('initialOf skips the honorific so cards are not all the same letter', () => {
  assert.equal(initialOf(d('श्री संजय जी जमदार', [])), 'स');   // संजय, not श्री
  assert.equal(initialOf(d('श्रीमती राजो बाई', [])), 'र');     // श्री must not shadow श्रीमती
  assert.equal(initialOf(d('स्वर्गीय श्री अमर जी भवानी', [])), 'अ');
  assert.equal(initialOf(d('स्व• आदित्य जी जमदार', [])), 'आ');
  assert.equal(initialOf(d('पंडित श्री मनोज जी उपाध्याय', [])), 'म');  // stacked markers
  assert.equal(initialOf(d('स्व. श्रीमती आशा जी जाट', [])), 'आ');
  assert.equal(initialOf({ name: { hi: '' }, items: [] }), '·');
});

test('every type code in TYPE_LABELS has both languages', () => {
  for (const [code, labels] of Object.entries(TYPE_LABELS)) {
    assert.ok(labels.hi, `${code} missing hi`);
    assert.ok(labels.en, `${code} missing en`);
  }
});

test('ordinal handles the teens and the 1/2/3 endings', () => {
  const want = { 1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 11: '11th', 12: '12th', 13: '13th',
    21: '21st', 22: '22nd', 23: '23rd', 24: '24th', 45: '45th', 46: '46th',
    111: '111th', 112: '112th', 113: '113th' };
  for (const [n, text] of Object.entries(want)) assert.equal(ordinal(Number(n)), text);
});

test('festivalHeading uses wan in Hindi and correct ordinals in English', () => {
  assert.equal(festivalHeading({ bhandara: 45, kanyaPujan: 22 }, 'hi'),
    '45वां विशाल भंडारा · 22वां नगर कन्या पूजन');
  assert.equal(festivalHeading({ bhandara: 46, kanyaPujan: 23 }, 'en'),
    '46th Vishal Bhandara · 23rd Nagar Kanya Pujan');
  assert.equal(festivalHeading(undefined, 'en'), '');
});

test('formatTotal formats rupees and unit quantities', () => {
  assert.equal(formatTotal({ type: 'cash', unit: 'inr', qty: 150900 }, 'hi'), '₹1,50,900');
  assert.equal(formatTotal({ type: 'sugar', unit: 'kg', qty: 1923 }, 'hi'), '1,923 किलो');
  assert.equal(formatTotal({ type: 'sugar', unit: 'kg', qty: 1923 }, 'en'), '1,923 kg');
});

test('totals come in vocabulary order, never ordered by quantity across units', () => {
  const donors = [
    d('x', [{ type: 'cash', qty: 99999, unit: 'inr' }, { type: 'zzz', qty: 5, unit: 'kg' },
            { type: 'ghee', qty: 1, unit: 'tin' }, { type: 'sugar', qty: 2, unit: 'kg' }]),
  ];
  assert.deepEqual(totals(donors).map((r) => r.type), ['sugar', 'ghee', 'cash', 'zzz']);
});

test('the English page orders by the English name where one exists', () => {
  const donors = [
    { name: { hi: 'श्री अजय', en: 'Shri Zubin' }, items: [] },
    { name: { hi: 'श्री बबलू' }, items: [] },
    { name: { hi: 'श्री चमन', en: 'Late Mohan' }, items: [] },
  ];
  assert.deepEqual(sortDonors(donors, 'name', 'en').map((x) => x.name.hi),
    ['श्री चमन', 'श्री अजय', 'श्री बबलू']);   // Mohan, Zubin, then Hindi-only (Latin sorts first)
  assert.deepEqual(sortDonors(donors, 'name', 'hi').map((x) => x.name.hi),
    ['श्री अजय', 'श्री चमन', 'श्री बबलू']);
});

test('श्रीकांत keeps its initial and sorts under श, while श्री क still strips', () => {
  assert.equal(initialOf(d('श्रीकांत जी', [])), 'श');
  assert.equal(initialOf(d('श्री कमल', [])), 'क');
  assert.equal(initialOf(d('डॉ.सेठिया', [])), 'स');
  const sorted = sortDonors([d('श्रीकांत', []), d('श्री अजय', []), d('श्री कमल', [])], 'name', 'hi');
  assert.equal(sorted[2].name.hi, 'श्रीकांत');
});

test('English totals band does not stutter "cylinder Gas cylinder"', () => {
  const row = { type: 'gas', unit: 'cylinder', qty: 7 };
  assert.equal(`${formatTotal(row, 'en')} ${typeLabel('gas', 'en')}`, '7 Gas cylinder');
});

test('English units pluralise; singular stays singular', () => {
  const f = (unit, qty) => formatTotal({ type: 'x', unit, qty }, 'en');
  assert.equal(f('tin', 1), '1 tin');
  assert.equal(f('tin', 31), '31 tins');
  assert.equal(f('jar', 152), '152 jars');
  assert.equal(f('piece', 1), '1 piece');
  assert.equal(f('piece', 2), '2 pieces');
});

test('nameIsHindiOnly: only English pages whose donor has no name.en', () => {
  const d = { name: { hi: 'श्री क' } };
  assert.equal(nameIsHindiOnly(d, 'en'), true);
  assert.equal(nameIsHindiOnly(d, 'hi'), false);
  assert.equal(nameIsHindiOnly({ name: { hi: 'क', en: 'Ka' } }, 'en'), false);
});

test('displayNameParts keeps the prefix apart from the name', () => {
  const p = displayNameParts({ name: { hi: 'श्री क' }, memoriam: true }, 'en');
  assert.deepEqual(p, { prefix: 'Late', name: 'श्री क', hindi: true });
});

test('temple materials read naturally in both languages', () => {
  const cases = [
    [{ type: 'cement', qty: 21, unit: 'bag' }, '21 बोरी सीमेंट', '21 bags Cement'],
    [{ type: 'cement', qty: 1, unit: 'bag' }, '1 बोरी सीमेंट', '1 bag Cement'],
    [{ type: 'brick', qty: 551, unit: 'count' }, '551 ईंट', '551 Bricks'],
    [{ type: 'rebar', qty: 51, unit: 'kg' }, '51 किलो सरिया', '51 kg Steel rods (sariya)'],
    [{ type: 'tiles', note: 'मंदिर प्रांगण में संपूर्ण' }, 'टाइल्स (मंदिर प्रांगण में संपूर्ण)', 'Tiles (मंदिर प्रांगण में संपूर्ण)'],
    [{ type: 'fan', note: 'मंदिर प्रांगण हेतु' }, 'छत का पंखा (मंदिर प्रांगण हेतु)', 'Ceiling fan (मंदिर प्रांगण हेतु)'],
  ];
  for (const [item, hi, en] of cases) {
    assert.equal(formatItems(d('x', [item]), 'hi'), hi);
    assert.equal(formatItems(d('x', [item]), 'en'), en);
  }
});

test('temple totals: bags and a bare count', () => {
  const rows = totals([d('a', [{ type: 'cement', qty: 21, unit: 'bag' }]),
                       d('b', [{ type: 'cement', qty: 5, unit: 'bag' }, { type: 'brick', qty: 551, unit: 'count' }])]);
  assert.deepEqual(rows.map((r) => formatTotal(r, 'en')), ['26 bags', '551']);
  assert.deepEqual(rows.map((r) => formatTotal(r, 'hi')), ['26 बोरी', '551']);
});

test('listSource: a year file, a named list, and nothing else', () => {
  assert.equal(listSource({ year: '2024' }).url, '/data/donors-2024.json');
  assert.equal(listSource({ year: '2024' }).named, false);
  assert.equal(listSource({ list: 'hanuman-mandir' }).url, '/data/hanuman-mandir.json');
  assert.equal(listSource({ list: 'hanuman-mandir' }).named, true);
  // The attribute becomes part of a URL: only a plain slug is accepted.
  for (const bad of ['../secret', 'a/b', 'donors-2025.json', '']) assert.equal(listSource({ list: bad }), null);
  assert.equal(listSource({ year: '20x4' }), null);
  assert.equal(listSource({}), null);
});

// The कावड़ यात्रा list records arrangements, not only goods: someone paid for
// a dharmshala or the meals at one stop of the यात्रा.
test('the यात्रा arrangements have labels in both languages', () => {
  assert.equal(typeLabel('lodging', 'hi'), 'धर्मशाला व्यवस्था');
  assert.equal(typeLabel('lodging', 'en'), 'Lodging arranged');
  assert.equal(typeLabel('meals', 'hi'), 'भोजन व्यवस्था');
  assert.equal(typeLabel('vehicle', 'hi'), 'वाहन व्यवस्था');
  assert.equal(typeLabel('vegetables', 'hi'), 'हरी सब्जियाँ');
  assert.equal(typeLabel('falahar', 'hi'), 'फलाहार');
  assert.equal(typeLabel('dal', 'hi'), 'दाल');
  for (const code of ['meals', 'vehicle', 'vegetables', 'falahar', 'dal']) {
    assert.ok(typeLabel(code, 'en') !== code, `${code} has no English label`);
  }
});

test('an arrangement with no quantity reads as the label, with its place in brackets', () => {
  const donor = { items: [{ type: 'lodging', note: 'ओंकारेश्वर में' }] };
  assert.equal(formatItems(donor, 'hi'), 'धर्मशाला व्यवस्था (ओंकारेश्वर में)');
});

// Grouping: the दान सूची page shows one block per kind of giving, so a reader
// can see at a glance who arranged the धर्मशाला and who gave नगद.
test('groupByType: one block per type, in the order the list introduces them', () => {
  const donors = [
    d('क', [{ type: 'lodging', note: 'ओंकारेश्वर में' }]),
    d('ख', [{ type: 'cash', qty: 1100, unit: 'inr' }]),
    d('ग', [{ type: 'lodging', note: 'बड़वाह में' }]),
    d('घ', [{ type: 'flour', qty: 51, unit: 'kg' }]),
  ];
  const groups = groupByType(donors, 'hi');
  assert.deepEqual(groups.map((g) => [g.type, g.label, g.donors.length]), [
    ['lodging', 'धर्मशाला व्यवस्था', 2],
    ['cash', 'नगद', 1],
    ['flour', 'आटा', 1],
  ]);
  // Within a block the समाज's own order survives.
  assert.deepEqual(groups[0].donors.map((x) => x.name.hi), ['क', 'ग']);
  assert.equal(groupByType(donors, 'en')[0].label, 'Lodging arranged');
});

test('groupByType: a donor who gave two things sits under the first, and only once', () => {
  const donors = [
    d('क', [{ type: 'flour', qty: 101, unit: 'kg' }, { type: 'cash', qty: 1100, unit: 'inr' }]),
    d('ख', [{ type: 'cash', qty: 500, unit: 'inr' }]),
  ];
  const groups = groupByType(donors, 'hi');
  assert.deepEqual(groups.map((g) => [g.type, g.donors.map((x) => x.name.hi)]),
    [['flour', ['क']], ['cash', ['ख']]]);
  // Every donor is shown exactly once, however many things they gave.
  assert.equal(groups.reduce((n, g) => n + g.donors.length, 0), donors.length);
});

test('groupByType: a gift with no type recorded falls under अन्य, not its own blank block', () => {
  const groups = groupByType([d('क', []), d('ख', [{ type: 'other', note: 'सेवा' }])], 'hi');
  assert.deepEqual(groups.map((g) => [g.type, g.label, g.donors.length]), [['other', 'अन्य', 2]]);
});

// Every row names what was given, even under a type block that says the same:
// a column of bare quantities ("200 किलो", "51 किलो") makes the reader look up
// to the heading to learn what they are counting.
test('formatItems always names the type, block heading or not', () => {
  assert.equal(formatItems(d('x', [{ type: 'lodging', note: 'ओंकारेश्वर में' }]), 'hi'),
    'धर्मशाला व्यवस्था (ओंकारेश्वर में)');
  assert.equal(formatItems(d('x', [{ type: 'cash', qty: 2100, unit: 'inr' }]), 'hi'), '₹2,100 नगद');
  assert.equal(formatItems(d('x', [{ type: 'flour', qty: 51, unit: 'kg' }]), 'hi'), '51 किलो आटा');
  assert.equal(formatItems(d('x', [{ type: 'lodging', note: 'Omkareshwar' }]), 'en'),
    'Lodging arranged (Omkareshwar)');
  assert.equal(formatItems(d('x', [{ type: 'flour', qty: 101, unit: 'kg' },
                                   { type: 'cash', qty: 1100, unit: 'inr' }]), 'hi'),
    '101 किलो आटा + ₹1,100 नगद');
  // A third argument is no longer read, so no row can be stripped by accident.
  assert.equal(formatItems(d('x', [{ type: 'flour', qty: 51, unit: 'kg' }]), 'hi', 'flour'),
    '51 किलो आटा');
});

test('a type with no quantity and no note still shows its name', () => {
  assert.equal(formatItems(d('x', [{ type: 'lodging' }]), 'hi'), 'धर्मशाला व्यवस्था');
});
