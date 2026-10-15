import test from 'node:test';
import assert from 'node:assert/strict';
import { createHistoryLoader } from './history-fetch.js';

const FILES = {
  '/data/donors.json': {
    donors: { D0001: { name: { hi: 'श्री संजू जाट' }, aliases: [] } },
    merged: { D0009: 'D0001' },
  },
  '/data/donors-index.json': { lists: ['hanuman-mandir'], years: [2024, 2025] },
  '/data/hanuman-mandir.json': { title: { hi: 'मंदिर' }, donors: [
    { name: { hi: 'श्री संजू जाट' }, donorIds: ['D0001'], items: [{ type: 'cement', qty: 21, unit: 'bag' }] }] },
  '/data/donors-2025.json': { donors: [
    { name: { hi: 'श्री संजू जाट' }, donorIds: ['D0009'], items: [{ type: 'cash', qty: 1100, unit: 'inr' }] }] },
  '/data/donors-2024.json': { donors: [] },
};

function fakeGetJSON(log, failFirst = false) {
  let calls = 0;
  return async (url) => {
    log.push(url);
    if (failFirst && ++calls === 1) throw new Error('HTTP 503 for ' + url);
    if (!(url in FILES)) throw new Error('HTTP 404 for ' + url);
    return structuredClone(FILES[url]);
  };
}

test('a history is gathered across every list, with merges followed', async () => {
  const history = createHistoryLoader(fakeGetJSON([]));
  const h = await history('D0009');
  assert.equal(h.id, 'D0001');
  assert.equal(h.count, 2);
  assert.deepEqual(h.groups.map((g) => g.list.key), ['hanuman-mandir', '2025']);
});

test('each file is fetched once, however many histories the pop-up asks for', async () => {
  const log = [];
  const history = createHistoryLoader(fakeGetJSON(log));
  await Promise.all([history('D0001'), history('D0009')]);
  await history('D0001');
  assert.deepEqual([...new Set(log)].sort(), log.slice().sort());   // no URL twice
  assert.equal(log.length, 5);
});

test('an unknown or malformed ID yields no history', async () => {
  const history = createHistoryLoader(fakeGetJSON([]));
  assert.equal(await history('D0404'), null);
  assert.equal(await history('nonsense'), null);
});

test('a failed load is not kept: the next ask tries again', async () => {
  const log = [];
  const history = createHistoryLoader(fakeGetJSON(log, true));
  await assert.rejects(history('D0001'), /503/);
  const h = await history('D0001');
  assert.equal(h.id, 'D0001');
});
