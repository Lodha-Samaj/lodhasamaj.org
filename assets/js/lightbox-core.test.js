import test from 'node:test';
import assert from 'node:assert/strict';
import { step, slideOf, counterText } from './lightbox-core.js';

test('step moves through the pictures and comes round at both ends', () => {
  assert.equal(step(0, 1, 12), 1);
  assert.equal(step(11, 1, 12), 0);     // past the last one is the first
  assert.equal(step(0, -1, 12), 11);    // and back the other way
  assert.equal(step(5, -1, 12), 4);
  assert.equal(step(0, 1, 1), 0);       // one picture: it stays put
});

test('step refuses nonsense rather than showing a blank frame', () => {
  for (const bad of [[NaN, 1, 12], [0, 1, 0], [0, 1, -3], ['x', 1, 12]]) {
    assert.equal(step(...bad), 0);
  }
});

test('slideOf copies what the thumbnail already knows', () => {
  const img = { src: '/assets/img/gallery/gr2.jpeg', alt: 'दुर्गा प्रतिमा के साथ समूह चित्र',
                naturalWidth: 1280, naturalHeight: 589 };
  assert.deepEqual(slideOf(img), {
    src: '/assets/img/gallery/gr2.jpeg', alt: 'दुर्गा प्रतिमा के साथ समूह चित्र',
    width: 1280, height: 589,
  });
  // A picture that has not loaded yet still opens, just without its size.
  assert.deepEqual(slideOf({ src: '/a.jpg', alt: '' }), { src: '/a.jpg', alt: '', width: 0, height: 0 });
});

test('the counter reads in the page\'s own language and numerals', () => {
  assert.equal(counterText(0, 12, 'hi'), '12 में से 1');
  assert.equal(counterText(11, 12, 'hi'), '12 में से 12');
  assert.equal(counterText(0, 12, 'en'), '1 of 12');
});
