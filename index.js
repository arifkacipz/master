export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 1. Jalur Reader: /asn/slug/ch-8 -> buka reader.html
    const readerMatch = path.match(/^\/asn\/([^/]+)\/ch-(\d+)\/?$/);
    if (readerMatch) {
      const slug = readerMatch[1];
      const ch = readerMatch[2];
      return fetch(`${url.origin}/asn/reader.html?slug=${slug}&ch=${ch}`);
    }

    // 2. Jalur Detail: /asn/slug -> buka detail.html
    const detailMatch = path.match(/^\/asn\/([^/]+)\/?$/);
    if (detailMatch && !detailMatch[1].includes('.')) {
      const slug = detailMatch[1];
      return fetch(`${url.origin}/asn/detail.html?slug=${slug}`);
    }

    // 3. Permintaan lainnya (file json, gambar, index2.html) biarkan normal
    return fetch(request);
  },
};
