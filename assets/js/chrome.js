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

// The four marks, drawn here as plain geometry instead of each platform's
// official artwork: they read at 20px, take currentColor, and keep the site
// free of an icon font or any file to fetch.
const SOCIAL_ICONS = {
  Facebook: '<circle cx="12" cy="12" r="9.2" fill="none" stroke="currentColor" stroke-width="1.6"/>'
    + '<path d="M14.8 7.3h-1.7c-1.3 0-2.2.9-2.2 2.3v1.3H9.3v2.2h1.6v5.6h2.3v-5.6h1.8l.3-2.2h-2.1V9.9c0-.4.2-.6.6-.6h1.4z"/>',
  Instagram: '<rect x="3.2" y="3.2" width="17.6" height="17.6" rx="5.2" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    + '<circle cx="12" cy="12" r="4.1" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    + '<circle cx="16.9" cy="7.1" r="1.15"/>',
  YouTube: '<rect x="2.4" y="5.4" width="19.2" height="13.2" rx="4" fill="none" stroke="currentColor" stroke-width="1.7"/>'
    + '<path d="M10.4 9.2 16 12l-5.6 2.8z"/>',
  WhatsApp: '<path d="M20.1 11.8a8.1 8.1 0 0 1-12 7.1L4 20l1.2-3.9a8.1 8.1 0 1 1 14.9-4.3z" fill="none"'
    + ' stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>'
    + '<path d="M9.5 8.7c.3-.1.6 0 .8.3l.8 1.3c.1.2.1.5-.1.7l-.5.5c-.1.1-.2.3-.1.5.5 1 1.3 1.8 2.3 2.3.2.1.4 0 .5-.1'
    + 'l.5-.5c.2-.2.5-.2.7-.1l1.3.8c.3.2.4.5.3.8-.2.7-.9 1.1-1.6 1.1-2.9-.3-5.2-2.6-5.5-5.5 0-.7.4-1.3 1.1-1.5z"/>',
};
const HEX = /^#[0-9a-f]{6}$/i;
const socialHtml = () => CONTACT.socials.map((s) => {
  const mark = SOCIAL_ICONS[s.label];
  const brand = HEX.test(s.brand || '') ? ` style="--brand:${s.brand}"` : '';
  return `<li><a href="${esc(s.href)}" rel="noopener" aria-label="${esc(s.label)}"${brand}>${
    mark ? `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">${mark}</svg>`
         : esc(s.label)}</a></li>`;
}).join('');

const footer = document.getElementById('site-footer');
if (footer) {
  const F = lang === 'hi'
    ? { name: 'लोधा समाज इंदौर', tag: 'सेवा · शिक्षा · स्वास्थ्य',
        contact: 'संपर्क', follow: 'हमसे जुड़ें' }
    : { name: 'Lodha Samaj Indore', tag: 'Service · Education · Health',
        contact: 'Contact', follow: 'Follow us' };
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="wrap site-footer-inner">
      <div class="f-brand">
        <b>${F.name}</b>
        <p class="f-tag">${F.tag}</p>
      </div>
      <div class="f-col">
        <h2 class="f-head">${F.contact}</h2>
        <p class="f-addr">${esc(CONTACT.address[lang])}</p>
        <p><a href="tel:${esc(CONTACT.phone.replace(/\s/g, ''))}">${esc(CONTACT.phone)}</a></p>${
          CONTACT.email ? `
        <p><a href="mailto:${esc(CONTACT.email)}">${esc(CONTACT.email)}</a></p>` : ''}
      </div>
      <div class="f-col">
        <h2 class="f-head">${F.follow}</h2>
        <ul class="socials">${socialHtml()}</ul>
      </div>
    </div>
    <div class="f-base"><div class="wrap">© ${new Date().getFullYear()} ${F.name}</div></div>`;
}
