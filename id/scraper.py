import os
import re
import json
import time
import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

BASE_DIR = "id"  # asumsikan script berada di dalam folder id/
DB_DIR = os.path.join(BASE_DIR, "id/db")

class KomikuScraper:
    def __init__(self):
        self.base_url = "https://komiku.org"
        self.api_base = "https://api.komiku.org/manga/"

    @staticmethod
    def extract_chapter_number(chapter_name):
        match = re.search(r'(\d+(?:\.\d+)?)', chapter_name)
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

    def merge_chapters(self, old_chapters, new_chapters):
        old_dict = {}
        for ch in old_chapters:
            num = self.extract_chapter_number(ch.get('nama', ''))
            if num is not None:
                old_dict[num] = ch
        for ch in new_chapters:
            num = self.extract_chapter_number(ch.get('nama', ''))
            if num is not None and num not in old_dict:
                old_dict[num] = ch
        merged = list(old_dict.values())
        merged.sort(key=lambda x: self.extract_chapter_number(x['nama']))
        return merged

    def save_to_db(self, slug, data):
        path = self.get_db_path(slug)
        old_data = self.load_existing(slug)
        if old_data:
            merged_chapters = self.merge_chapters(old_data.get('chapters', []), data.get('chapters', []))
            final_data = {
                "judul": data.get("judul", old_data.get("judul", slug)),
                "judul_alternatif": data.get("judul_alternatif", old_data.get("judul_alternatif", "")),
                "slug": slug,
                "thumb": data.get("thumb", old_data.get("thumb", "")),
                "tipe": data.get("tipe", old_data.get("tipe", "")),
                "status": data.get("status", old_data.get("status", "")),
                "genre": data.get("genre", old_data.get("genre", [])),
                "sinopsis": data.get("sinopsis", old_data.get("sinopsis", "")),
                "author": data.get("author", old_data.get("author", "")),
                "rating": data.get("rating", old_data.get("rating", "")),
                "pembaca_total": data.get("pembaca_total", old_data.get("pembaca_total", 0)),
                "pembaca_mingguan": data.get("pembaca_mingguan", old_data.get("pembaca_mingguan", 0)),
                "cara_baca": data.get("cara_baca", old_data.get("cara_baca", "")),
                "source": "komiku",
                "online": len(merged_chapters),
                "chapterCount": len(merged_chapters),
                "Chs": ", ".join([ch['nama'] for ch in merged_chapters]),
                "chapters": merged_chapters,
                "last_scraped": datetime.datetime.now().isoformat()
            }
        else:
            final_data = data
            final_data['slug'] = slug
            final_data['source'] = "komiku"
            final_data['online'] = len(data.get('chapters', []))
            final_data['chapterCount'] = len(data.get('chapters', []))
            final_data['Chs'] = ", ".join([ch['nama'] for ch in data.get('chapters', [])])
            final_data['last_scraped'] = datetime.datetime.now().isoformat()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        return final_data

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
                    judul_tag = item.select_one('.kan h3')
                    judul = judul_tag.get_text(strip=True) if judul_tag else slug.replace('-', ' ').title()
                    img = item.select_one('.bgei img')
                    thumb = img.get('src') if img else ''
                    manga_list.append({
                        "judul": judul,
                        "slug": slug,
                        "url": link,
                        "thumb": thumb
                    })
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
            # Judul
            judul_tag = soup.select_one('#Judul h1 span[itemprop="name"]')
            judul = judul_tag.get_text(strip=True) if judul_tag else None
            if not judul:
                h1 = soup.find('h1')
                judul = h1.get_text(strip=True) if h1 else "Unknown"
            # Thumbnail
            og_img = soup.find('meta', property='og:image')
            thumb = og_img['content'] if og_img and og_img.get('content') else ''
            if not thumb:
                ims_img = soup.select_one('#Informasi .ims img')
                thumb = ims_img.get('src') if ims_img else ''
            # Info table
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
            judul_alternatif = info.get('Judul Alternatif', '')
            author = info.get('Author', '')
            rating = info.get('Rating', '')
            cara_baca = info.get('Cara Baca', '')
            # Genre
            genre_list = [span.get_text(strip=True) for span in soup.select('ul.genre li a span')]
            # Pembaca
            pembaca_text = info.get('Pembaca', '')
            pembaca_total = pembaca_mingguan = 0
            if pembaca_text:
                total_match = re.search(r'Total:\s*([\d.]+)\s*views', pembaca_text)
                minggu_match = re.search(r'Minggu ini:\s*([\d.]+)\s*views', pembaca_text)
                if total_match:
                    pembaca_total = int(total_match.group(1).replace('.', ''))
                if minggu_match:
                    pembaca_mingguan = int(minggu_match.group(1).replace('.', ''))
            # Sinopsis
            sinopsis_tag = soup.find('p', class_='desc')
            sinopsis = sinopsis_tag.get_text(strip=True) if sinopsis_tag else ''
            # Chapters
            chapters = []
            chapter_table = soup.find('table', id='Daftar_Chapter')
            if chapter_table:
                for tr in chapter_table.find('tbody').find_all('tr'):
                    td_judul = tr.find('td', class_='judulseries')
                    td_tanggal = tr.find('td', class_='tanggalseries')
                    if not td_judul or not td_tanggal:
                        continue
                    a = td_judul.find('a', href=True)
                    if not a:
                        continue
                    href = a['href']
                    if href.startswith('/'):
                        href = self.base_url + href
                    nama = a.find('span', itemprop='name').find('b').get_text(strip=True) if a.find('span', itemprop='name') and a.find('span', itemprop='name').find('b') else a.get_text(strip=True)
                    tanggal = td_tanggal.get_text(strip=True)
                    chapters.append({
                        "nama": nama,
                        "url": href,
                        "tanggal_rilis": tanggal
                    })
            return {
                "judul": judul,
                "judul_alternatif": judul_alternatif,
                "thumb": thumb,
                "tipe": tipe,
                "status": status,
                "genre": genre_list,
                "sinopsis": sinopsis,
                "author": author,
                "rating": rating,
                "pembaca_total": pembaca_total,
                "pembaca_mingguan": pembaca_mingguan,
                "cara_baca": cara_baca,
                "chapters": chapters
            }
        except Exception as e:
            print(f"Error scrape_detail: {e}")
            return None

    def scrape_chapter(self, chapter_url):
        try:
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            if res.status_code != 200:
                return []
            soup = BeautifulSoup(res.text, 'html.parser')
            reader = soup.find('div', id='Baca_Komik')
            if not reader:
                return []
            images = []
            for img in reader.find_all('img'):
                src = img.get('src')
                if src and src.startswith('http') and '.svg' not in src:
                    images.append(src)
            # deduplicate
            seen = set()
            unique = [u for u in images if not (u in seen or seen.add(u))]
            return unique
        except Exception as e:
            print(f"Error scrape_chapter: {e}")
            return []

    def process_manga(self, slug, url, limit_ch=None):
        print(f"Processing: {slug}")
        detail = self.scrape_detail(url)
        if not detail:
            return None
        all_chapters = detail.get('chapters', [])
        old_data = self.load_existing(slug)
        existing_nums = set()
        if old_data:
            for ch in old_data.get('chapters', []):
                num = self.extract_chapter_number(ch['nama'])
                if num is not None:
                    existing_nums.add(num)
        new_chapters = []
        for ch in all_chapters:
            num = self.extract_chapter_number(ch['nama'])
            if num is not None and num not in existing_nums:
                new_chapters.append(ch)
        new_chapters.sort(key=lambda x: self.extract_chapter_number(x['nama']) or 0)
        if limit_ch:
            new_chapters = new_chapters[-limit_ch:]
        print(f"New chapters to scrape: {len(new_chapters)}")
        for ch in new_chapters:
            ch['images'] = self.scrape_chapter(ch['url'])
            print(f"  {ch['nama']}: {len(ch['images'])} images")
            time.sleep(0.5)
        # Gabungkan dengan data lama
        merged = self.merge_chapters(old_data['chapters'] if old_data else [], new_chapters)
        final_data = {
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
        return self.save_to_db(slug, final_data)

def generate_list():
    all_manga = []
    for root, dirs, files in os.walk(DB_DIR):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                slug = file[:-5]
                all_manga.append({
                    "judul": data.get("judul", slug),
                    "slug": slug,
                    "thumb": data.get("thumb", ""),
                    "tipe": data.get("tipe", ""),
                    "status": data.get("status", ""),
                    "genre": data.get("genre", []),
                    "pembaca_total": data.get("pembaca_total", 0),
                    "chapterCount": data.get("chapterCount", 0),
                    "last_scraped": data.get("last_scraped", "")
                })
    all_manga.sort(key=lambda x: x["last_scraped"], reverse=True)
    with open(os.path.join(BASE_DIR, 'list.json'), 'w', encoding='utf-8') as f:
        json.dump(all_manga, f, indent=2, ensure_ascii=False)
    print(f"list.json updated ({len(all_manga)} manga)")

def generate_stats():
    stats = []
    for root, dirs, files in os.walk(DB_DIR):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                slug = file[:-5]
                stats.append({
                    "slug": slug,
                    "judul": data.get("judul", slug),
                    "thumb": data.get("thumb", ""),
                    "online": data.get("online", 0),
                    "chapterCount": data.get("chapterCount", 0)
                })
    low = [c for c in stats if c['online'] < 15]
    with open(os.path.join(BASE_DIR, 'stats.json'), 'w', encoding='utf-8') as f:
        json.dump(low, f, indent=2, ensure_ascii=False)
    print(f"stats.json updated ({len(low)} manga)")

def health_check():
    # Cek jumlah file JSON di db/
    count = sum(1 for root, dirs, files in os.walk(DB_DIR) for f in files if f.endswith('.json'))
    health = {
        "last_run": datetime.datetime.now().isoformat(),
        "total_manga": count,
        "status": "ok"
    }
    with open(os.path.join(BASE_DIR, 'health.json'), 'w') as f:
        json.dump(health, f, indent=2)
    print("health.json updated")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--slug', help='Single manga slug')
    parser.add_argument('--catalog', action='store_true', help='Run catalog')
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
        # fallback to env TARGET_SLUG
        slug = os.environ.get('TARGET_SLUG')
        if slug:
            url = f"https://komiku.org/manga/{slug}/"
            scraper.process_manga(slug, url, limit_ch=args.limit)

    generate_list()
    generate_stats()
    health_check()
