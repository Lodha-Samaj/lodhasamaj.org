import { NAV, CONTACT } from './nav.js';

const lang = document.documentElement.lang.toLowerCase().startsWith('en') ? 'en' : 'hi';
const base = `/${lang}/`;
const here = location.pathname;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function navHtml() {
  return NAV.map(({ href, ...labels }) => {
    const url = `${base}${href}`;
    const current = here === url || (href && here.startsWith(url));
    return `<a href="${url}"${current ? ' aria-current="page"' : ''}>${esc(labels[lang])}</a>`;
  }).join('');
}

function langToggleHtml() {
  const alt = document.querySelector(
    `link[rel="alternate"][hreflang]:not([hreflang="${lang}"]):not([hreflang="x-default"])`);
  if (!alt) return '';                       // no counterpart: hide the toggle
  const other = lang === 'hi' ? 'EN' : 'हि';
  return `<a class="lang-toggle" href="${esc(alt.getAttribute('href'))}"
             hreflang="${esc(alt.hreflang)}" lang="${esc(alt.hreflang)}">${other}</a>`;
}

// WCAG 2.4.1: let keyboard users jump past the ~12 header links.
const main = document.querySelector('main');
if (main) {
  if (!main.id) main.id = 'main-content';
  main.setAttribute('tabindex', '-1');       // so the jump moves focus, not just scroll
  const skip = document.createElement('a');
  skip.className = 'skip-link';
  skip.href = `#${main.id}`;
  skip.textContent = lang === 'hi' ? 'मुख्य सामग्री पर जाएँ' : 'Skip to main content';
  document.body.prepend(skip);
}

const header = document.getElementById('site-header');
if (header) {
  header.className = 'site-header';
  header.innerHTML = `
    <div class="gold-line"></div>
    <div class="wrap site-header-inner">
      <a class="brand" href="${base}">
        <img src="/assets/img/logo.png" alt="" width="60" height="52">
        <span><b>${lang === 'hi' ? 'लोधा समाज इंदौर' : 'Lodha Samaj Indore'}</b>
        <i>${lang === 'hi' ? 'सेवा · शिक्षा · स्वास्थ्य' : 'Service · Education · Health'}</i></span>
      </a>
      <button class="nav-toggle" aria-expanded="false"
              aria-controls="site-nav" aria-label="${lang === 'hi' ? 'मेनू' : 'Menu'}">☰</button>
      <nav id="site-nav" class="site-nav" aria-label="${lang === 'hi' ? 'मुख्य मेनू' : 'Main'}">${navHtml()}</nav>
      ${langToggleHtml()}
      <a class="cta" href="${base}daan/">${lang === 'hi' ? 'दान कीजिए' : 'Donate'}</a>
    </div>`;

  const button = header.querySelector('.nav-toggle');
  const nav = header.querySelector('#site-nav');
  const setOpen = (open) => {
    button.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('open', open);
  };
  button.addEventListener('click', () => {
    setOpen(button.getAttribute('aria-expanded') !== 'true');
  });
  document.addEventListener('keydown', (e) => {
    if (e.defaultPrevented) return;
    if (e.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      button.focus();
    }
  });
}

const footer = document.getElementById('site-footer');
if (footer) {
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="wrap site-footer-inner">
      <div>
        <b>${lang === 'hi' ? 'लोधा समाज इंदौर' : 'Lodha Samaj Indore'}</b>
        <p>${esc(CONTACT.address[lang])}</p>
      </div>
      <div>
        <a href="tel:${esc(CONTACT.phone.replace(/\s/g, ''))}">${esc(CONTACT.phone)}</a>${
          CONTACT.email ? `<br>
        <a href="mailto:${esc(CONTACT.email)}">${esc(CONTACT.email)}</a>` : ''}
      </div>
      <div class="socials">${CONTACT.socials.map((s) =>
        `<a href="${esc(s.href)}" rel="noopener">${esc(s.label)}</a>`).join('')}</div>
    </div>`;
}
