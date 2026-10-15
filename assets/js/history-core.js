// Pure donor-history logic: one Donor ID's gifts across every list.
// No DOM, no fetch - testable with node:test, like donors-core.js.

import { totals } from './donors-core.js';

export const DONOR_ID = /^D\d{4}$/;

/** "?id= d0042 " -> "D0042". Only trims and upper-cases; resolveId judges it. */
export function normalizeIdParam(raw) {
  return String(raw ?? '').trim().toUpperCase();
}

/** The kept ID for `id` (following a merge), or null if malformed or unknown. */
export function resolveId(register, id) {
  if (!register || typeof id !== 'string' || !DONOR_ID.test(id)) return null;
  const target = register.merged?.[id] ?? id;
  return register.donors?.[target] ? target : null;
}

/** Newest first: named lists (campaigns, in index order), then years descending. */
export function listOrder(index) {
  const named = (index?.lists || []).map((key) => ({ key, kind: 'list' }));
  const years = [...(index?.years || [])].filter(Number.isInteger).sort((a, b) => b - a)
    .map((year) => ({ key: String(year), kind: 'year', year }));
  return [...named, ...years];
}

export const listDataUrl = (list) =>
  (list.kind === 'year' ? `/data/donors-${list.key}.json` : `/data/${list.key}.json`);
export const listPageUrl = (list, lang) => `/${lang}/daan/${list.key}/`;
export const historyUrl = (id, lang) => `/${lang}/daata/?id=${id}`;

/** "/hi/daata/?id=D0042" -> "D0042". null for anything that is not a Donor ID. */
export function idFromHistoryHref(href) {
  const raw = String(href ?? '').match(/[?&]id=([^&#]*)/)?.[1];
  if (raw === undefined) return null;
  const id = normalizeIdParam(decodeURIComponent(raw));
  return DONOR_ID.test(id) ? id : null;
}

/** Everything one donor gave. `lists`: [{key, kind, year?, data}] in display order. */
export function gatherHistory(register, lists, id) {
  const canonical = resolveId(register, id);
  if (!canonical) return null;
  const donor = register.donors[canonical];
  const groups = [];
  for (const list of lists) {
    const entries = [];
    for (const entry of list.data?.donors || []) {
      const ids = [...new Set((entry.donorIds || []).map((x) => resolveId(register, x)).filter(Boolean))];
      if (!ids.includes(canonical)) continue;
      const partners = ids.filter((x) => x !== canonical)
        .map((x) => ({ id: x, name: register.donors[x].name }));
      entries.push({ entry, partners });
    }
    if (entries.length) groups.push({ list, entries });
  }
  const all = groups.flatMap((g) => g.entries.map((e) => e.entry));
  return {
    id: canonical, merged: canonical !== id, name: donor.name, aliases: donor.aliases || [],
    groups, count: all.length, listCount: groups.length, totals: totals(all),
  };
}

/** "संयुक्त: A एवं B के साथ" / "Joint with A and B". */
export function partnerNote(names, lang) {
  if (!names.length) return '';
  if (lang === 'hi') return `संयुक्त: ${names.join(' एवं ')} के साथ`;
  return `Joint with ${names.join(' and ')}`;
}

const nameIn = (register, id, lang) => {
  const n = register?.donors?.[id]?.name;
  return (n && (n[lang] || n.hi)) || id;
};

/** Links for the pop-up: one generic link, or one per person on a joint gift. */
export function historyLinks(entry, register, lang) {
  const raw = (entry.donorIds || []).filter((x) => DONOR_ID.test(x));
  const ids = [...new Set(raw.map((x) => resolveId(register, x) || (register ? null : x)).filter(Boolean))];
  if (ids.length === 1) {
    return [{ id: ids[0], href: historyUrl(ids[0], lang), text: lang === 'hi' ? 'पूरा दान इतिहास →' : 'Full donation history →' }];
  }
  return ids.map((id) => ({
    id,
    href: historyUrl(id, lang),
    // "दान इतिहास", never "का इतिहास": what is listed is the giving, not the person.
    text: lang === 'hi'
      ? `${nameIn(register, id, lang)} का दान इतिहास →`
      : `Donation history of ${nameIn(register, id, lang)} →`,
  }));
}
