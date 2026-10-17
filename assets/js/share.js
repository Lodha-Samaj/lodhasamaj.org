// The साझा page's copy buttons.
//
// Each button starts out hidden in the HTML and is only revealed here, once we
// know this browser can actually copy. A button that looks ready and then does
// nothing is worse than no button: the text is right there to select by hand,
// and that path always works.
const boxes = [...document.querySelectorAll('.copy-btn')];

const lang = document.documentElement.lang.toLowerCase().startsWith('en') ? 'en' : 'hi';
const T = lang === 'hi'
  ? { copy: 'नक़ल कीजिए', done: 'नक़ल हो गई', failed: 'नक़ल नहीं हुई — हाथ से चुन लीजिए' }
  : { copy: 'Copy', done: 'Copied', failed: 'Could not copy — select it by hand' };

/** Put `text` on the clipboard. The modern call needs a secure page and a
 *  permission that can be refused; the old one needs a selection in the
 *  document. Try the first, fall back to the second, and report honestly if
 *  neither worked rather than pretending. */
async function copy(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch { /* refused or not permitted here - try the older way */ }
  }
  const pad = document.createElement('textarea');
  pad.value = text;
  // Off-screen rather than hidden: a display:none field cannot be selected.
  pad.setAttribute('aria-hidden', 'true');
  pad.style.cssText = 'position:fixed;top:-1000px;left:-1000px;opacity:0';
  document.body.append(pad);
  pad.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch { ok = false; }
  pad.remove();
  return ok;
}

// A place to announce the result to a screen reader, which cannot see a button
// change colour.
const say = document.createElement('p');
say.className = 'sr-only';
say.setAttribute('role', 'status');
say.setAttribute('aria-live', 'polite');
document.body.append(say);

for (const button of boxes) {
  const source = document.getElementById(button.dataset.copy);
  if (!source) continue;
  button.hidden = false;
  let settle;
  button.addEventListener('click', async () => {
    const ok = await copy(source.textContent);
    button.textContent = ok ? T.done : T.failed;
    button.classList.toggle('is-done', ok);
    say.textContent = button.textContent;
    clearTimeout(settle);
    settle = setTimeout(() => {
      button.textContent = T.copy;
      button.classList.remove('is-done');
    }, ok ? 2000 : 4000);
  });
}
