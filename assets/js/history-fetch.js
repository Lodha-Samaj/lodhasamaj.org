// Loading the data a donation history needs: the register, the list index and
// every list. The pop-up may ask for one history after another, so a loader
// fetches each file once and answers the rest from memory.

import { listOrder, listDataUrl, gatherHistory } from './history-core.js';

export async function fetchJSON(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
  return response.json();
}

export function createHistoryLoader(getJSON = fetchJSON) {
  let sources = null;

  function load() {
    if (sources) return sources;
    sources = (async () => {
      const [register, index] = await Promise.all([
        getJSON('/data/donors.json'), getJSON('/data/donors-index.json'),
      ]);
      const order = listOrder(index);
      const datas = await Promise.all(order.map((list) => getJSON(listDataUrl(list))));
      return { register, lists: order.map((list, i) => ({ ...list, data: datas[i] })) };
    })();
    // A dropped connection must not poison the loader: forget a failed load so
    // the next click tries again.
    sources.catch(() => { sources = null; });
    return sources;
  }

  return async function history(id) {
    const { register, lists } = await load();
    return gatherHistory(register, lists, id);
  };
}
