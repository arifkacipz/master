export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Tambahan: Jika akses /asn/ atau /asn maka buka index.html
    if (path === '/asn' || path === '/asn/') {
      return fetch(`${url.origin}/asn/index.html`);
    }

    // 1. Jalur Reader: /asn/slug/ch-8
    const readerMatch = path.match(/^\/asn\/([^/]+)\/ch-(\d+)\/?$/);
    if (readerMatch) {
      return fetch(`${url.origin}/asn/reader.html?slug=${readerMatch[1]}&ch=${readerMatch[2]}`);
    }

    // 2. Jalur Detail: /asn/slug
    const detailMatch = path.match(/^\/asn\/([^/]+)\/?$/);
    if (detailMatch && !detailMatch[1].includes('.')) {
      return fetch(`${url.origin}/asn/detail.html?slug=${detailMatch[1]}`);
    }

    return fetch(request);
  },
};
