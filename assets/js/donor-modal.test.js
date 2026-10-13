import test from 'node:test';
import assert from 'node:assert/strict';
import { nextIndex } from './donor-modal.js';

test('nextIndex advances and wraps forward', () => {
  assert.equal(nextIndex(0, 1, 44), 1);
  assert.equal(nextIndex(43, 1, 44), 0);
});

test('nextIndex wraps backward past zero', () => {
  assert.equal(nextIndex(0, -1, 44), 43);
  assert.equal(nextIndex(5, -1, 44), 4);
});

test('nextIndex is safe when the filtered set is empty or has one item', () => {
  assert.equal(nextIndex(0, 1, 0), 0);
  assert.equal(nextIndex(0, 1, 1), 0);
  assert.equal(nextIndex(0, -1, 1), 0);
});

test('nextIndex clamps an index left stale by a filter change', () => {
  // The visible set shrank from 44 to 3 while the modal was open.
  assert.equal(nextIndex(40, 1, 3), 0);
  assert.equal(nextIndex(40, -1, 3), 2);
});

test('nextIndex with delta 0 (the refresh path) keeps a valid index and clamps a stale one', () => {
  assert.equal(nextIndex(1, 0, 3), 1);
  assert.equal(nextIndex(40, 0, 3), 2);
});

test('nextIndex treats current === length as stale', () => {
  assert.equal(nextIndex(3, 1, 3), 0);
  assert.equal(nextIndex(3, -1, 3), 2);
});
