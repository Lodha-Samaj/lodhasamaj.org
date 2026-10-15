import test from 'node:test';
import assert from 'node:assert/strict';
import { gatherHistory } from './history-core.js';
import { historyHtml, historyDocTitle } from './history-view.js';

const register = {
  donors: {
    D0001: { name: { hi: 'श्री संजू जाट' }, aliases: ['श्री संजू जाट', 'श्री संजू जी जाट'] },
    D0002: { name: { hi: 'श्री कमल जाट', en: 'Shri Kamal Jat' }, aliases: ['श्री कमल जाट'] },
  },
  merged: { D0009: 'D0001' },
};
const lists = [
  { key: 'hanuman-mandir', kind: 'list', data: { title: { hi: 'मंदिर', en: 'Temple' }, donors: [
    { name: { hi: 'श्री संजू जाट एवं श्री कमल जाट' }, donorIds: ['D0001', 'D0002'],
      items: [{ type: 'cement', qty: 21, unit: 'bag' }] }] } },
  { key: '2025', kind: 'year', year: 2025, data: { donors: [
    { name: { hi: 'श्री संजू जी जाट' }, donorIds: ['D0009'], items: [{ type: 'cash', qty: 1100, unit: 'inr' }] }] } },
];
const history = (id = 'D0001') => gatherHistory(register, lists, id);

test('the markup names the donor, the Donor ID and how much they gave in all', () => {
  const html = historyHtml(history(), 'hi');
  assert.match(html, /<h1[^>]*>श्री संजू जाट<\/h1>/);
  assert.match(html, /दानदाता क्रमांक <b>D0001<\/b>/);
  assert.match(html, /2 दान · 2 सूचियाँ/);
  assert.match(html, /₹1,100/);                       // the totals row
  assert.match(html, /संयुक्त दान सहित/);              // the note under it
});

test('every list the donor appears in becomes a section linking to that list', () => {
  const html = historyHtml(history(), 'hi');
  assert.match(html, /<a href="\/hi\/daan\/hanuman-mandir\/">मंदिर<\/a>/);
  assert.match(html, /<a href="\/hi\/daan\/2025\/">2025 दानदाता सूची<\/a>/);
  assert.match(html, /21 बोरी सीमेंट/);
  // Newest first: the named list comes before the year, as listOrder decided.
  assert.ok(html.indexOf('hanuman-mandir') < html.indexOf('/hi/daan/2025/'));
});

test('a joint gift names the partner and links to their own history', () => {
  const html = historyHtml(history(), 'hi');
  assert.match(html, /संयुक्त: <a href="\/hi\/daata\/\?id=D0002">श्री कमल जाट<\/a> के साथ/);
});

test('an alias the lists used is shown, but never the name already in the heading', () => {
  const html = historyHtml(history(), 'hi');
  const [, aliasLine] = html.match(/<p class="donor-aliases">(.*?)<\/p>/);
  assert.equal(aliasLine, 'सूचियों में अन्य नाम: श्री संजू जी जाट');
});

test('on the English page a Hindi-only name is marked lang="hi", an English one is not', () => {
  const html = historyHtml(history(), 'en');
  assert.match(html, /<h1[^>]*><span lang="hi">श्री संजू जाट<\/span><\/h1>/);
  assert.match(html, /Joint with <a href="\/en\/daata\/\?id=D0002">Shri Kamal Jat<\/a>/);
  assert.match(html, /2 gifts · 2 lists/);
});

test('a name carrying markup is escaped, not rendered', () => {
  const nasty = { ...register, donors: { ...register.donors, D0001: { name: { hi: '<img src=x>' }, aliases: [] } } };
  const html = historyHtml(gatherHistory(nasty, lists, 'D0001'), 'hi');
  assert.ok(!html.includes('<img src=x>'));
  assert.match(html, /&lt;img src=x&gt;/);
});

test('the pop-up can ask for its own heading level and id, to label the dialog', () => {
  const html = historyHtml(history(), 'hi', { heading: 'h2', headingId: 'dm-history-name' });
  assert.match(html, /<h2 id="dm-history-name" tabindex="-1">श्री संजू जाट<\/h2>/);
  assert.ok(!html.includes('<h1'));
});

test('the document title pairs the donor with the page name', () => {
  assert.equal(historyDocTitle(history(), 'hi'), 'श्री संजू जाट — दान इतिहास');
  assert.equal(historyDocTitle(history(), 'en'), 'श्री संजू जाट — Donation history');
});
