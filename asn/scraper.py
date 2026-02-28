import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader
import argparse

# ================== KONFIGURASI CLOUDINARY ==================
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'X-Requested-With': 'XMLHttpRequest'
}

# ================== FUNGSI BANTU UMUM ==================
def extract_chapter_number(chapter_name):
    """Ekstrak nomor chapter dari string (misal 'Chapter 45' -> 45.0)."""
    match = re.search(r'(\d+(?:\.\d+)?)', chapter_name)
    return float(match.group(1)) if match else None

def merge_chapters(old_chapters, new_chapters):
    """
    Menggabungkan dua daftar chapter dengan menggunakan NOMOR CHAPTER sebagai kunci unik.
    - Jika nomor chapter sudah ada di daftar lama, data baru untuk nomor tersebut akan diabaikan.
    - Hanya chapter dengan nomor yang belum ada yang akan ditambahkan.
    Hasil diurutkan berdasarkan nomor chapter.
    """
    old_dict = {}
    for ch in old_chapters:
        if 'url' not in ch:
            continue
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            old_dict[num] = ch

    for ch in new_chapters:
        if 'url' not in ch:
            continue
        num = extract_chapter_number(ch['nama'])
        if num is None:
            continue
        if num not in old_dict:
            old_dict[num] = ch

    merged = list(old_dict.values())
    merged.sort(key=lambda x: extract_chapter_number(x['nama']))
    return merged

def upload_to_cloudinary(image_url, public_id, folder="petomic_thumbs"):
    """Upload gambar ke Cloudinary dan return URL aman."""
    try:
        up = cloudinary.uploader.upload(
            image_url,
            public_id=public_id,
            folder=folder,
            overwrite=True
        )
        return up['secure_url']
    except Exception as e:
        print(f"Cloudinary upload gagal: {e}")
        return image_url  # Fallback ke URL asli

def save_to_db(slug, data):
    """Simpan data ke file db/{slug}.json."""
    os.makedirs('db', exist_ok=True)
    path = f'db/{slug}.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_from_db(slug):
    """Load data dari file db/{slug}.json jika ada dan valid."""
    path = f'db/{slug}.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return None

# ================== FUNGSI UNTUK MANHUAPLUS ==================
def get_images_manhuaplus(chapter_url):
    """Mengambil semua URL gambar dari halaman chapter manhuaplus."""
    try:
        # Ekstrak Chapter ID dari URL
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match:
                chapter_id = match.group(1)
            else:
                return []

        # Ambil data gambar via AJAX POST
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)

        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
                # Filter duplikat dan loading.gif
                seen = set()
                temp_list = []
                for img in list_gambar:
                    img = img.strip()
                    if "loading.gif" not in img and img not in seen:
                        temp_list.append(img)
                        seen.add(img)
                temp_list.sort()
                return temp_list
        return []
    except Exception as e:
        print(f"Error get_images_manhuaplus: {e}")
        return []

def process_comic_manhuaplus(judul, link, slug, thumb_url=None, limit_ch=None):
    """Memproses satu komik dari manhuaplus."""
    print(f"--- ManhuaPlus memproses: {judul} ---")
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Ambil judul asli dari halaman
        h1 = soup.select_one('h1')
        if h1:
            judul_asli = h1.get_text(strip=True)
            if judul_asli:
                judul = judul_asli

        # Ambil thumbnail jika belum ada
        if not thumb_url:
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                thumb_url = og_img['content']
            else:
                img_tag = soup.select_one('.summary_image img, .thumb img')
                if img_tag:
                    thumb_url = img_tag.get('src') or img_tag.get('data-src')
                if thumb_url and not thumb_url.startswith('http'):
                    thumb_url = 'https://manhuaplus.org' + thumb_url

        thumb_cloud = upload_to_cloudinary(thumb_url, slug) if thumb_url else ""

        # Ambil daftar chapter
        ch_list = []
        ul_chapter = soup.select_one('ul#myUL')
        if ul_chapter:
            for li in ul_chapter.select('li.chapter'):
                a = li.select_one('a')
                if a and a.get('href'):
                    url = a['href']
                    nama = a.get_text(strip=True) or li.get('data', '')
                    ch_list.append({"nama": nama, "url": url})

        # Cadangan: JSON-LD
        if not ch_list:
            scripts = soup.find_all('script', type='application/ld+json')
            for s in scripts:
                try:
                    js_data = json.loads(s.string)
                    graph = js_data.get('@graph', [js_data])
                    for g in graph:
                        if g.get('@type') == 'ItemList':
                            for item in g.get('itemListElement', []):
                                u = item.get('url')
                                if u and '/chapters/' in u:
                                    name = u.split('/')[-2].replace('-', ' ').title()
                                    ch_list.append({"nama": name, "url": u})
                except:
                    continue

        # Cadangan: dropdown
        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})

        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Terapkan limit jika diminta
        if limit_ch:
            ch_list = ch_list[:limit_ch]

        # Ambil gambar setiap chapter
        final_chapters = []
        for ch in ch_list:
            print(f"   -> Scraping Chapter: {ch['nama']}")
            imgs = get_images_manhuaplus(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "url": ch['url'], "images": imgs})
            time.sleep(0.8)

        if not final_chapters:
            print(f"Tidak ada gambar berhasil diambil untuk {slug}")
            return None

        # Urutan baca: dari terlama ke terbaru
        final_chapters.reverse()

        # Gabung dengan data lama (hanya tambah chapter dengan nomor baru)
        old_data = load_from_db(slug)
        if old_data and 'chapters' in old_data:
            old_chapters = old_data['chapters']
            if all('url' in ch for ch in old_chapters):
                final_chapters = merge_chapters(old_chapters, final_chapters)
                print(f"   -> Setelah digabung: total {len(final_chapters)} chapter")
            else:
                print("   -> File lama tidak valid, ditimpa dengan data baru")
        else:
            # Tidak ada data lama, gunakan final_chapters apa adanya
            pass

        # Simpan hasil (tambahkan field source)
        result = {
            "judul": judul,
            "thumb": thumb_cloud,
            "source": "manhuaplus",
            "chapters": final_chapters
        }
        save_to_db(slug, result)
        print(f"SUKSES: {slug}.json tersimpan (total {len(final_chapters)} chapter).")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def scrape_manhuaplus_catalog(max_pages=10):
    """Ambil daftar manga dari halaman katalog manhuaplus."""
    base_url = "https://manhuaplus.org/all-manga/"
    list_manga = []
    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}{page}/?sort=last_update&status=0"
        print(f"Scraping manhuaplus halaman {page}: {url}")
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('div.mh-77vh > div, .page-item-detail, .listupd .bs')
        if not items:
            break
        for item in items:
            link_tag = item.select_one('a.fw-600, .post-title a, h3 a')
            if not link_tag:
                continue
            judul = link_tag.text.strip()
            link = link_tag['href']
            slug = link.split('/')[-1] if not link.endswith('/') else link.split('/')[-2]
            img_tag = item.select_one('img')
            thumb = img_tag.get('data-src') or img_tag.get('src')
            if thumb and not thumb.startswith('http'):
                thumb = "https://manhuaplus.org" + thumb
            list_manga.append({
                "judul": judul,
                "slug": slug,
                "thumb": thumb,
                "url": link
            })
        time.sleep(1)
    return list_manga

# ================== FUNGSI UNTUK ARENASCAN ==================
def get_images_arenascan(chapter_url):
    """Ambil semua URL gambar dari halaman chapter arenascan."""
    try:
        res = requests.get(chapter_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        img_urls = []

        # --- METODE 1: Cari langsung di div#readerarea ---
        readerarea = soup.find('div', id='readerarea')
        if readerarea:
            # Cari semua tag img (mungkin sudah dimuat)
            imgs = readerarea.find_all('img')
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and 'loading' not in src and src.startswith('http'):
                    img_urls.append(src)

            # Jika kosong, cari di dalam <noscript>
            if not img_urls:
                noscript = readerarea.find('noscript')
                if noscript and noscript.string:
                    noscript_soup = BeautifulSoup(noscript.string, 'html.parser')
                    imgs = noscript_soup.find_all('img')
                    for img in imgs:
                        src = img.get('src')
                        if src and src.startswith('http'):
                            img_urls.append(src)

        # --- METODE 2: Ekstrak dari ts_reader.run (jika ada) ---
        if not img_urls:
            script_pattern = r'ts_reader\.run\(({.*?})\);'
            scripts = soup.find_all('script', text=re.compile(script_pattern))
            for script in scripts:
                match = re.search(script_pattern, script.string)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        sources = data.get('sources', [])
                        if sources:
                            images = sources[0].get('images', [])
                            if images:
                                img_urls = images
                                break
                    except:
                        continue

        # --- METODE 3: Fallback cari semua img di halaman (jika dua metode di atas gagal) ---
        if not img_urls:
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src and 'avatar' not in src and src.startswith('http'):
                    img_urls.append(src)

        # Hapus duplikat dan urutkan
        seen = set()
        unique = []
        for u in img_urls:
            if u not in seen:
                unique.append(u)
                seen.add(u)
        return unique

    except Exception as e:
        print(f"Error get_images_arenascan: {e}")
        return []

def process_comic_arenascan(judul, link, slug, thumb_url=None, limit_ch=None):
    """Memproses satu komik dari arenascan."""
    print(f"--- Arenascan memproses: {judul} ---")
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Ambil judul dari h1
        h1 = soup.select_one('h1.entry-title')
        if h1:
            judul = h1.get_text(strip=True)

        # Ambil thumbnail jika belum ada
        if not thumb_url:
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                thumb_url = og_img['content']
            else:
                img_tag = soup.select_one('.thumb img, .summary_image img')
                if img_tag:
                    thumb_url = img_tag.get('src') or img_tag.get('data-src')
                if thumb_url and not thumb_url.startswith('http'):
                    thumb_url = 'https://arenascan.com' + thumb_url

        thumb_cloud = upload_to_cloudinary(thumb_url, slug) if thumb_url else ""

        # Ambil daftar chapter dari div#chapterlist ul
        chapterlist = soup.select_one('#chapterlist ul')
        if not chapterlist:
            print(f"Tidak ada daftar chapter ditemukan untuk {slug}")
            return None

        ch_list = []
        for li in chapterlist.select('li'):
            a = li.select_one('a[href]')
            if not a:
                continue
            url = a['href']
            # Nama chapter dari span.chapternum
            chapternum = a.select_one('.chapternum')
            nama = chapternum.get_text(strip=True) if chapternum else a.get_text(strip=True)
            ch_list.append({"nama": nama, "url": url})

        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Daftar chapter biasanya dari terbaru ke terlama, balik agar terlama dulu
        ch_list.reverse()

        # Terapkan limit jika diminta
        if limit_ch:
            ch_list = ch_list[:limit_ch]

        # Ambil gambar setiap chapter
        final_chapters = []
        for ch in ch_list:
            print(f"   -> Scraping Chapter: {ch['nama']}")
            imgs = get_images_arenascan(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "url": ch['url'], "images": imgs})
            time.sleep(0.8)

        if not final_chapters:
            print(f"Tidak ada gambar berhasil diambil untuk {slug}")
            return None

        # Gabung dengan data lama (hanya tambah chapter dengan nomor baru)
        old_data = load_from_db(slug)
        if old_data and 'chapters' in old_data:
            old_chapters = old_data['chapters']
            if all('url' in ch for ch in old_chapters):
                final_chapters = merge_chapters(old_chapters, final_chapters)
                print(f"   -> Setelah digabung: total {len(final_chapters)} chapter")
            else:
                print("   -> File lama tidak valid, ditimpa dengan data baru")
        else:
            # Tidak ada data lama, gunakan final_chapters apa adanya
            pass

        # Simpan hasil (tambahkan field source)
        result = {
            "judul": judul,
            "thumb": thumb_cloud,
            "source": "arenascan",
            "chapters": final_chapters
        }
        save_to_db(slug, result)
        print(f"SUKSES: {slug}.json tersimpan (total {len(final_chapters)} chapter).")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def scrape_arenascan_catalog(max_pages=10):
    """Ambil daftar manga dari halaman katalog arenascan."""
    base_url = "https://arenascan.com/manga/"
    list_manga = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}?page={page}&order=update"
        print(f"Scraping arenascan halaman {page}: {url}")
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('div.listupd div.bs')
        if not items:
            break
        for item in items:
            a = item.select_one('a[href]')
            if not a:
                continue
            url = a['href']
            slug = url.rstrip('/').split('/')[-1]
            judul = a.get('title', '').strip() or a.select_one('.tt').get_text(strip=True)
            img = a.select_one('img')
            thumb = img.get('src') or img.get('data-src') if img else ''
            list_manga.append({
                "judul": judul,
                "slug": slug,
                "thumb": thumb,
                "url": url
            })
        time.sleep(1)
    return list_manga

# ================== FUNGSI KATALOG ==================
def run_catalog_mode(max_pages=3, limit_ch=3):
    """Menjalankan scraping katalog dari kedua sumber."""
    print("=== SCRAPING KATALOG MANHUAPLUS ===")
    manga_list_manhuaplus = scrape_manhuaplus_catalog(max_pages=max_pages)
    for manga in manga_list_manhuaplus:
        process_comic_manhuaplus(
            judul=manga['judul'],
            link=manga['url'],
            slug=manga['slug'],
            thumb_url=manga['thumb'],
            limit_ch=limit_ch
        )
        time.sleep(2)

    print("\n=== SCRAPING KATALOG ARENASCAN ===")
    manga_list_arenascan = scrape_arenascan_catalog(max_pages=max_pages)
    for manga in manga_list_arenascan:
        process_comic_arenascan(
            judul=manga['judul'],
            link=manga['url'],
            slug=manga['slug'],
            thumb_url=manga['thumb'],
            limit_ch=limit_ch
        )
        time.sleep(2)

    # Buat list.json gabungan
    all_manga = []
    for filename in os.listdir('db'):
        if filename.endswith('.json'):
            with open(os.path.join('db', filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_manga.append({
                    "judul": data.get("judul", ""),
                    "slug": filename[:-5],
                    "thumb": data.get("thumb", "")
                })
    with open('list.json', 'w', encoding='utf-8') as f:
        json.dump(all_manga, f, indent=4)
    print(f"\nlist.json diperbarui dengan {len(all_manga)} manga.")

# ================== MAIN dengan ARGPARSE ==================
def main():
    parser = argparse.ArgumentParser(description='Scrape komik dari manhuaplus.org dan arenascan.com')
    parser.add_argument('--slug', help='Slug komik (contoh: nama-komik)')
    parser.add_argument('--source', choices=['manhuaplus', 'arenascan', 'auto'], default='auto',
                        help='Sumber data (default auto: coba manhuaplus dulu, lalu arenascan)')
    parser.add_argument('--catalog', action='store_true', help='Jalankan mode katalog (mengabaikan slug)')
    parser.add_argument('--pages', type=int, default=3, help='Jumlah halaman katalog (default 3)')
    parser.add_argument('--limit', type=int, default=3, help='Jumlah chapter terbaru yang diambil di mode katalog (default 3)')
    args = parser.parse_args()

    if args.catalog:
        # Mode katalog via argumen
        run_catalog_mode(max_pages=args.pages, limit_ch=args.limit)
        return

    if args.slug:
        # Mode satu slug dengan argumen
        if args.source == 'auto':
            # Coba manhuaplus dulu
            url = f"https://manhuaplus.org/manga/{args.slug}"
            result = process_comic_manhuaplus(
                judul=args.slug.replace('-', ' ').title(),
                link=url,
                slug=args.slug,
                thumb_url=None,
                limit_ch=None
            )
            if not result:
                # Coba arenascan
                url = f"https://arenascan.com/manga/{args.slug}/"
                result = process_comic_arenascan(
                    judul=args.slug.replace('-', ' ').title(),
                    link=url,
                    slug=args.slug,
                    thumb_url=None,
                    limit_ch=None
                )
            if not result:
                print(f"Gagal mengambil data untuk slug {args.slug} dari kedua sumber.")
        elif args.source == 'manhuaplus':
            url = f"https://manhuaplus.org/manga/{args.slug}"
            process_comic_manhuaplus(
                judul=args.slug.replace('-', ' ').title(),
                link=url,
                slug=args.slug,
                thumb_url=None,
                limit_ch=None
            )
        else:  # arenascan
            url = f"https://arenascan.com/manga/{args.slug}/"
            process_comic_arenascan(
                judul=args.slug.replace('-', ' ').title(),
                link=url,
                slug=args.slug,
                thumb_url=None,
                limit_ch=None
            )
        return

    # Jika tidak ada argumen, gunakan environment variables (kompatibilitas ke belakang)
    target_slug = os.environ.get('TARGET_SLUG')
    source = os.environ.get('SOURCE', 'manhuaplus').lower()
    if target_slug:
        # Mode satu slug via env
        if source == 'manhuaplus':
            url = f"https://manhuaplus.org/manga/{target_slug}"
            process_comic_manhuaplus(
                judul=target_slug.replace('-', ' ').title(),
                link=url,
                slug=target_slug,
                thumb_url=None,
                limit_ch=None
            )
        elif source == 'arenascan':
            url = f"https://arenascan.com/manga/{target_slug}/"
            process_comic_arenascan(
                judul=target_slug.replace('-', ' ').title(),
                link=url,
                slug=target_slug,
                thumb_url=None,
                limit_ch=None
            )
        else:
            print(f"Source tidak dikenal: {source}. Gunakan 'manhuaplus' atau 'arenascan'.")
    else:
        # Mode katalog via env (default)
        run_catalog_mode(max_pages=3, limit_ch=3)

if __name__ == "__main__":
    main()
