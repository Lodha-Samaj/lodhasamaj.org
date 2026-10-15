import test from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeIdParam, resolveId, listOrder, listDataUrl, listPageUrl, gatherHistory,
  partnerNote, historyLinks, historyUrl, idFromHistoryHref,
} from './history-core.js';

const register = {
  donors: {
    D0001: { name: { hi: 'श्री संजू जाट' }, aliases: ['श्री संजू जाट', 'श्री संजू जी जाट'] },
    D0002: { name: { hi: 'श्री कमल जाट' }, aliases: ['श्री कमल जाट'] },
  },
  merged: { D0009: 'D0001' },
};
const cash = (qty) => ({ type: 'cash', qty, unit: 'inr' });
const lists = [
  { key: 'hanuman-mandir', kind: 'list', data: { title: { hi: 'मंदिर', en: 'Temple' }, donors: [
    { name: { hi: 'श्री संजू जाट एवं श्री कमल जाट' }, donorIds: ['D0001', 'D0002'],
      items: [{ type: 'cement', qty: 21, unit: 'bag' }] }] } },
  { key: '2025', kind: 'year', year: 2025, data: { donors: [
    { name: { hi: 'श्री संजू जी जाट' }, donorIds: ['D0009'], items: [cash(1100)] },
    { name: { hi: 'श्री ख' }, donorIds: ['D0003'], items: [cash(5)] }] } },
];

test('an ID from the address is trimmed and upper-cased, nothing more', () => {
  assert.equal(normalizeIdParam(' d0042 '), 'D0042');
  assert.equal(normalizeIdParam(null), '');
});

test('resolveId follows a merge and refuses anything malformed or unknown', () => {
  assert.equal(resolveId(register, 'D0001'), 'D0001');
  assert.equal(resolveId(register, 'D0009'), 'D0001');
  for (const bad of ['D0042', 'D42', 'd0001', '', null, '../x']) assert.equal(resolveId(register, bad), null);
});

test('lists are searched newest first: named lists, then years descending', () => {
  assert.deepEqual(listOrder({ years: [2024, 2025], lists: ['hanuman-mandir'] }), [
    { key: 'hanuman-mandir', kind: 'list' },
    { key: '2025', kind: 'year', year: 2025 },
    { key: '2024', kind: 'year', year: 2024 }]);
  assert.equal(listDataUrl({ key: '2025', kind: 'year' }), '/data/donors-2025.json');
  assert.equal(listDataUrl({ key: 'hanuman-mandir', kind: 'list' }), '/data/hanuman-mandir.json');
  assert.equal(listPageUrl({ key: '2025', kind: 'year' }, 'en'), '/en/daan/2025/');
});

test('gatherHistory collects every gift, follows merges and names joint partners', () => {
  const h = gatherHistory(register, lists, 'D0009');
  assert.equal(h.id, 'D0001');
  assert.equal(h.merged, true);
  assert.equal(h.count, 2);
  assert.equal(h.listCount, 2);
  assert.deepEqual(h.groups.map((g) => g.list.key), ['hanuman-mandir', '2025']);
  assert.deepEqual(h.groups[0].entries[0].partners, [{ id: 'D0002', name: { hi: 'श्री कमल जाट' } }]);
  assert.deepEqual(h.totals.map((t) => `${t.type}|${t.unit}|${t.qty}`), ['cash|inr|1100', 'cement|bag|21']);
  assert.equal(gatherHistory(register, lists, 'D0042'), null);
});

test('partnerNote reads naturally in both languages', () => {
  assert.equal(partnerNote(['श्री कमल जाट'], 'hi'), 'संयुक्त: श्री कमल जाट के साथ');
  assert.equal(partnerNote(['A', 'B'], 'hi'), 'संयुक्त: A एवं B के साथ');
  assert.equal(partnerNote(['A', 'B'], 'en'), 'Joint with A and B');
});

test('historyLinks: one generic link, one per person when joint, none when anonymous', () => {
  const [single, joint] = [lists[1].data.donors[0], lists[0].data.donors[0]];
  assert.deepEqual(historyLinks(single, register, 'hi'),
    [{ id: 'D0001', href: '/hi/daata/?id=D0001', text: 'पूरा दान इतिहास →' }]);
  assert.deepEqual(historyLinks(joint, register, 'en').map((l) => l.text),
    ['History of श्री संजू जाट →', 'History of श्री कमल जाट →']);
  assert.deepEqual(historyLinks(joint, register, 'hi').map((l) => l.text),
    ['श्री संजू जाट का इतिहास →', 'श्री कमल जाट का इतिहास →']);
  assert.deepEqual(historyLinks({ donorIds: [] }, register, 'hi'), []);
  // Register not loaded yet: still link, by ID.
  assert.deepEqual(historyLinks(joint, null, 'hi').map((l) => l.href),
    ['/hi/daata/?id=D0001', '/hi/daata/?id=D0002']);
  assert.equal(historyUrl('D0002', 'en'), '/en/daata/?id=D0002');
});

test('idFromHistoryHref reads the ID back out of a history link, and refuses anything else', () => {
  assert.equal(idFromHistoryHref('/hi/daata/?id=D0042'), 'D0042');
  assert.equal(idFromHistoryHref('https://lodhasamaj.org/en/daata/?id=d0042'), 'D0042');
  assert.equal(idFromHistoryHref('/hi/daan/2025/'), null);
  assert.equal(idFromHistoryHref('/hi/daata/?id=nonsense'), null);
  assert.equal(idFromHistoryHref(undefined), null);
});

test('historyLinks carries the canonical ID with each link, so the pop-up need not parse the href', () => {
  const joint = { donorIds: ['D0001', 'D0002'] };
  assert.deepEqual(historyLinks(joint, register, 'hi').map((l) => l.id), ['D0001', 'D0002']);
  // A merged ID resolves to the kept one.
  assert.deepEqual(historyLinks({ donorIds: ['D0009'] }, register, 'hi').map((l) => l.id), ['D0001']);
});
