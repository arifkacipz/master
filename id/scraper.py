import os
import re
import json
import time
import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ---------- Lokasi script ini (folder id/) ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # <-- folder id/
DB_DIR = os.path.join(BASE_DIR, 'db')

class KomikuScraper:
    def __init__(self):
        self.base_url = "https://komiku.org"
        self.api_base = "https://api.komiku.org/manga/"

    @staticmethod
    def extract_chapter_number(name):
        match = re.search(r'(\d+(?:\.\d+)?)', name)
        return float(match.group(1)) if match else None

    def get_db_path(self, slug):
        first_char = slug[0].lower() if slug else 'others'
        folder = first_char if first_char.isalnum() else 'others'
        os.makedirs(os.path.join(DB_DIR, folder), exist_ok=True)
        return os.path.join(DB_DIR, folder, f'{slug}.json')

    def load_existing(self, slug):
        path = self.get_db_path(slug)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def merge_chapters(self, old, new):
        old_dict = {}
        for ch in old:
            num = self.extract_chapter_number(ch.get('nama', ''))
            if num is not None:
                old_dict[num] = ch
        for ch in new:
            num = self.extract_chapter_number(ch.get('nama', ''))
            if num is not None and num not in old_dict:
                old_dict[num] = ch
        merged = list(old_dict.values())
        merged.sort(key=lambda x: self.extract_chapter_number(x['nama']))
        return merged

    def save_to_db(self, slug, data):
        path = self.get_db_path(slug)
        old = self.load_existing(slug)
        if old:
            merged = self.merge_chapters(old.get('chapters', []), data.get('chapters', []))
            final = {
                "judul": data.get("judul", old.get("judul", slug)),
                "judul_alternatif": data.get("judul_alternatif", old.get("judul_alternatif", "")),
                "slug": slug,
                "thumb": data.get("thumb", old.get("thumb", "")),
                "tipe": data.get("tipe", old.get("tipe", "")),
                "status": data.get("status", old.get("status", "")),
                "genre": data.get("genre", old.get("genre", [])),
                "sinopsis": data.get("sinopsis", old.get("sinopsis", "")),
                "author": data.get("author", old.get("author", "")),
                "rating": data.get("rating", old.get("rating", "")),
                "pembaca_total": data.get("pembaca_total", old.get("pembaca_total", 0)),
                "pembaca_mingguan": data.get("pembaca_mingguan", old.get("pembaca_mingguan", 0)),
                "cara_baca": data.get("cara_baca", old.get("cara_baca", "")),
                "source": "komiku",
                "online": len(merged),
                "chapterCount": len(merged),
                "Chs": ", ".join([ch['nama'] for ch in merged]),
                "chapters": merged,
                "last_scraped": datetime.datetime.now().isoformat()
            }
        else:
            final = data
            final['slug'] = slug
            final['source'] = "komiku"
            final['online'] = len(data.get('chapters', []))
            final['chapterCount'] = len(data.get('chapters', []))
            final['Chs'] = ", ".join([ch['nama'] for ch in data.get('chapters', [])])
            final['last_scraped'] = datetime.datetime.now().isoformat()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(final, f, indent=2, ensure_ascii=False)
        return final

    def scrape_catalog(self, max_pages=5):
        manga_list = []
        for page in range(1, max_pages + 1):
            url = self.api_base if page == 1 else f"{self.api_base}page/{page}/"
            print(f"Katalog hal {page}: {url}")
            try:
                res = requests.get(url, headers=HEADERS, timeout=20)
                if res.status_code != 200:
                    break
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.find_all('div', class_='bge')
                if not items:
                    break
                for item in items:
                    a = item.select_one('.bgei a[href]')
                    if not a:
                        continue
                    link = a['href']
                    slug = link.rstrip('/').split('/')[-1]
                    judul = item.select_one('.kan h3')
                    judul = judul.get_text(strip=True) if judul else slug.replace('-', ' ').title()
                    img = item.select_one('.bgei img')
                    thumb = img.get('src') if img else ''
                    manga_list.append({"judul": judul, "slug": slug, "url": link, "thumb": thumb})
                time.sleep(0.3)
            except Exception as e:
                print(f"Error: {e}")
                break
        return manga_list

    def scrape_detail(self, url):
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code != 200:
                return None
            soup = BeautifulSoup(res.text, 'html.parser')
            judul = soup.select_one('#Judul h1 span[itemprop="name"]')
            judul = judul.get_text(strip=True) if judul else (
                soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown")
            og = soup.find('meta', property='og:image')
            thumb = og['content'] if og and og.get('content') else ''
            if not thumb:
                ims = soup.select_one('#Informasi .ims img')
                thumb = ims.get('src') if ims else ''
            # info table
            info = {}
            table = soup.find('table', class_='inftable')
            if table:
                for tr in table.find_all('tr'):
                    tds = tr.find_all('td')
                    if len(tds) >= 2:
                        key = tds[0].get_text(strip=True).rstrip(':')
                        value = tds[1].get_text(strip=True)
                        info[key] = value
            tipe = info.get('Tipe', '')
            status = info.get('Status', '')
            author = info.get('Author', '')
            rating = info.get('Rating', '')
            cara_baca = info.get('Cara Baca', '')
            judul_alt = info.get('Judul Alternatif', '')
            genre = [span.get_text(strip=True) for span in soup.select('ul.genre li a span')]
            pembaca = info.get('Pembaca', '')
            total = minggu = 0
            if pembaca:
                m_total = re.search(r'Total:\s*([\d.]+)\s*views', pembaca)
                m_minggu = re.search(r'Minggu ini:\s*([\d.]+)\s*views', pembaca)
                if m_total: total = int(m_total.group(1).replace('.', ''))
                if m_minggu: minggu = int(m_minggu.group(1).replace('.', ''))
            sinopsis = soup.find('p', class_='desc')
            sinopsis = sinopsis.get_text(strip=True) if sinopsis else ''
            # chapters
            chapters = []
            ctable = soup.find('table', id='Daftar_Chapter')
            if ctable:
                for tr in ctable.find('tbody').find_all('tr'):
                    td_j = tr.find('td', class_='judulseries')
                    td_t = tr.find('td', class_='tanggalseries')
                    if not td_j or not td_t: continue
                    a = td_j.find('a', href=True)
                    if not a: continue
                    href = a['href']
                    if href.startswith('/'): href = self.base_url + href
                    nama = a.find('span', itemprop='name')
                    if nama and nama.find('b'):
                        nama = nama.find('b').get_text(strip=True)
                    else:
                        nama = a.get_text(strip=True)
                    tanggal = td_t.get_text(strip=True)
                    chapters.append({"nama": nama, "url": href, "tanggal_rilis": tanggal})
            return {
                "judul": judul, "judul_alternatif": judul_alt, "thumb": thumb,
                "tipe": tipe, "status": status, "genre": genre,
                "sinopsis": sinopsis, "author": author, "rating": rating,
                "pembaca_total": total, "pembaca_mingguan": minggu,
                "cara_baca": cara_baca, "chapters": chapters
            }
        except Exception as e:
            print(f"Error scrape_detail: {e}")
            return None

    def scrape_chapter(self, url):
        try:
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code != 200: return []
            soup = BeautifulSoup(res.text, 'html.parser')
            reader = soup.find('div', id='Baca_Komik')
            if not reader: return []
            imgs = [img['src'] for img in reader.find_all('img') if img.get('src') and img['src'].startswith('http') and '.svg' not in img['src']]
            # dedup
            seen = set()
            uniq = [x for x in imgs if not (x in seen or seen.add(x))]
            return uniq
        except Exception as e:
            print(f"Error scrape_chapter: {e}")
            return []

    def process_manga(self, slug, url, limit_ch=None):
        print(f"Processing: {slug}")
        detail = self.scrape_detail(url)
        if not detail: return None
        all_chapters = detail.get('chapters', [])
        old = self.load_existing(slug)
        existing_nums = set()
        if old:
            for ch in old.get('chapters', []):
                n = self.extract_chapter_number(ch['nama'])
                if n is not None: existing_nums.add(n)
        new_chapters = []
        for ch in all_chapters:
            n = self.extract_chapter_number(ch['nama'])
            if n is not None and n not in existing_nums:
                new_chapters.append(ch)
        new_chapters.sort(key=lambda x: self.extract_chapter_number(x['nama']) or 0)
        if limit_ch: new_chapters = new_chapters[-limit_ch:]
        print(f"New chapters to scrape: {len(new_chapters)}")
        for ch in new_chapters:
            ch['images'] = self.scrape_chapter(ch['url'])
            print(f"  {ch['nama']}: {len(ch['images'])} images")
            time.sleep(0.5)
        merged = self.merge_chapters(old['chapters'] if old else [], new_chapters)
        data = {
            "judul": detail["judul"],
            "judul_alternatif": detail.get("judul_alternatif", ""),
            "thumb": detail["thumb"],
            "tipe": detail.get("tipe", ""),
            "status": detail.get("status", ""),
            "genre": detail.get("genre", []),
            "sinopsis": detail.get("sinopsis", ""),
            "author": detail.get("author", ""),
            "rating": detail.get("rating", ""),
            "pembaca_total": detail.get("pembaca_total", 0),
            "pembaca_mingguan": detail.get("pembaca_mingguan", 0),
            "cara_baca": detail.get("cara_baca", ""),
            "chapters": merged
        }
        return self.save_to_db(slug, data)

if __name__ == '__main__':
    import argparse, os, time
    parser = argparse.ArgumentParser()
    parser.add_argument('--slug')
    parser.add_argument('--catalog', action='store_true')
    parser.add_argument('--pages', type=int, default=3)
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()

    scraper = KomikuScraper()

    if args.catalog:
        manga_list = scraper.scrape_catalog(max_pages=args.pages)
        for m in manga_list:
            scraper.process_manga(m['slug'], m['url'], limit_ch=args.limit)
            time.sleep(1)
    elif args.slug:
        url = f"https://komiku.org/manga/{args.slug}/"
        scraper.process_manga(args.slug, url, limit_ch=args.limit)
    else:
        slug = os.environ.get('TARGET_SLUG')
        if slug:
            url = f"https://komiku.org/manga/{slug}/"
            scraper.process_manga(slug, url, limit_ch=args.limit)
