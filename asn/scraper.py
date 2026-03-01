import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader
import argparse
from collections import OrderedDict

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

def merge_chapters_by_number(old_chapters, new_chapters):
    """
    Menggabungkan dua daftar chapter berdasarkan nomor chapter.
    - Jika nomor chapter sudah ada di old, pertahankan yang lama (tidak ditimpa).
    - Jika nomor chapter baru, tambahkan.
    Hasil diurutkan berdasarkan nomor chapter.
    """
    old_dict = {}
    for ch in old_chapters:
        num = extract_chapter_number(ch.get('nama', ''))
        if num is not None:
            old_dict[num] = ch

    for ch in new_chapters:
        num = extract_chapter_number(ch.get('nama', ''))
        if num is not None and num not in old_dict:
            old_dict[num] = ch

    merged = list(old_dict.values())
    merged.sort(key=lambda x: extract_chapter_number(x['nama']))
    return merged

def save_to_db(slug, new_data):
    """
    Menyimpan data ke db/{slug}.json dengan menggabungkan chapter baru
    dengan chapter yang sudah ada (berdasarkan nomor chapter).
    Field `online` dan `Chs` akan diperbarui sesuai nilai di new_data.
    """
    os.makedirs('db', exist_ok=True)
    path = f'db/{slug}.json'

    old_data = load_from_db(slug)
    if old_data:
        # Gabungkan chapter
        old_chapters = old_data.get('chapters', [])
        new_chapters = new_data.get('chapters', [])
        merged_chapters = merge_chapters_by_number(old_chapters, new_chapters)
        # Pertahankan judul dan thumb dari new_data (bisa juga pilih salah satu)
        judul = new_data.get('judul', old_data.get('judul', slug))
        thumb = new_data.get('thumb', old_data.get('thumb', ''))
        source = new_data.get('source', old_data.get('source', 'unknown'))
        online = new_data.get('online', len(merged_chapters))
        chs = new_data.get('Chs', ', '.join([ch['nama'] for ch in merged_chapters]))
        final_data = {
            "judul": judul,
            "thumb": thumb,
            "source": source,
            "online": online,
            "Chs": chs,
            "chapters": merged_chapters
        }
    else:
        final_data = new_data

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)

def check_image_url(url):
    """Periksa apakah URL gambar dapat diakses (HEAD request)."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.status_code == 200
    except:
        return False

def check_chapter_health(chapter):
    """Periksa kesehatan chapter dengan mengecek gambar pertama."""
    images = chapter.get('images', [])
    if not images:
        return False
    return check_image_url(images[0])

# ================== FUNGSI AMBIL DAFTAR CHAPTER (TANPA GAMBAR) ==================
def get_chapter_list_manhuaplus(link):
    """Ambil daftar chapter dari halaman detail manhuaplus (tanpa gambar)."""
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Gagal mengakses {link}, status code: {res.status_code}")
            return []
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []
        ul = soup.select_one('ul#myUL')
        if ul:
            for li in ul.select('li.chapter'):
                a = li.select_one('a')
                if a and a.get('href'):
                    url = a['href']
                    nama = a.get_text(strip=True) or li.get('data', '')
                    ch_list.append({"nama": nama, "url": url})
        # Fallback JSON-LD
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
        # Fallback dropdown
        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})
        return ch_list
    except Exception as e:
        print(f"Error get_chapter_list_manhuaplus: {e}")
        return []

def get_chapter_list_arenascan(link):
    """Ambil daftar chapter dari halaman detail arenascan (tanpa gambar)."""
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Gagal mengakses {link}, status code: {res.status_code}")
            return []
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []
        chapterlist = soup.select_one('#chapterlist ul')
        if chapterlist:
            for li in chapterlist.select('li'):
                a = li.select_one('a[href]')
                if not a:
                    continue
                url = a['href']
                chapternum = a.select_one('.chapternum')
                nama = chapternum.get_text(strip=True) if chapternum else a.get_text(strip=True)
                ch_list.append({"nama": nama, "url": url})
        return ch_list
    except Exception as e:
        print(f"Error get_chapter_list_arenascan: {e}")
        return []

def get_merged_chapter_list(slug):
    """Menggabungkan daftar chapter dari manhuaplus dan arenascan berdasarkan nomor chapter."""
    merged = OrderedDict()
    
    manhua_list = get_chapter_list_manhuaplus(f"https://manhuaplus.org/manga/{slug}")
    for ch in manhua_list:
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            if num not in merged:
                merged[num] = ch['nama']
    
    arena_list = get_chapter_list_arenascan(f"https://arenascan.com/manga/{slug}/")
    for ch in arena_list:
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            if num not in merged:
                merged[num] = ch['nama']
    
    sorted_items = sorted(merged.items())
    return [nama for _, nama in sorted_items]

# ================== FUNGSI AMBIL GAMBAR CHAPTER ==================
def get_images_manhuaplus(chapter_url):
    """Mengambil semua URL gambar dari halaman chapter manhuaplus."""
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match:
                chapter_id = match.group(1)
            else:
                return []
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
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

def get_images_arenascan(chapter_url):
    """Ambil semua URL gambar dari halaman chapter arenascan."""
    try:
        res = requests.get(chapter_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        img_urls = []

        # METODE 1: div#readerarea
        readerarea = soup.find('div', id='readerarea')
        if readerarea:
            imgs = readerarea.find_all('img')
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and 'loading' not in src and src.startswith('http'):
                    img_urls.append(src)
            if not img_urls:
                noscript = readerarea.find('noscript')
                if noscript and noscript.string:
                    noscript_soup = BeautifulSoup(noscript.string, 'html.parser')
                    imgs = noscript_soup.find_all('img')
                    for img in imgs:
                        src = img.get('src')
                        if src and src.startswith('http'):
                            img_urls.append(src)

        # METODE 2: ts_reader.run
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

        # METODE 3: fallback semua img
        if not img_urls:
            all_imgs = soup.find_all('img')
            for img in all_imgs:
                src = img.get('src') or img.get('data-src')
                if src and 'logo' not in src and 'avatar' not in src and src.startswith('http'):
                    img_urls.append(src)

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

# ================== FUNGSI MEMPROSES SATU SUMBER (DENGAN GAMBAR) ==================
def process_comic_manhuaplus(judul, link, slug, thumb_url=None, limit_ch=None, save=True):
    """Memproses satu komik dari manhuaplus. Jika save=False, hanya mengembalikan data tanpa menyimpan."""
    print(f"--- ManhuaPlus memproses: {judul} ---")
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Gagal mengakses {link}, status code: {res.status_code}")
            return None
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

        # Ambil daftar chapter (tanpa gambar dulu)
        ch_list = []
        ul_chapter = soup.select_one('ul#myUL')
        if ul_chapter:
            for li in ul_chapter.select('li.chapter'):
                a = li.select_one('a')
                if a and a.get('href'):
                    url = a['href']
                    nama = a.get_text(strip=True) or li.get('data', '')
                    ch_list.append({"nama": nama, "url": url})

        # Fallback jika tidak ditemukan
        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Terapkan limit jika diminta (ambil chapter terbaru)
        if limit_ch:
            ch_list = ch_list[:limit_ch]

        # Balik urutan menjadi terlama -> terbaru untuk pemrosesan
        ch_list.reverse()

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

        result = {
            "judul": judul,
            "thumb": thumb_cloud if save else thumb_url,
            "source": "manhuaplus",
            "chapters": final_chapters
        }

        return result

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def process_comic_arenascan(judul, link, slug, thumb_url=None, limit_ch=None, save=True):
    """Memproses satu komik dari arenascan. Jika save=False, hanya mengembalikan data tanpa menyimpan."""
    print(f"--- Arenascan memproses: {judul} ---")
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Gagal mengakses {link}, status code: {res.status_code}")
            return None
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

        # Ambil daftar chapter
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
            chapternum = a.select_one('.chapternum')
            nama = chapternum.get_text(strip=True) if chapternum else a.get_text(strip=True)
            ch_list.append({"nama": nama, "url": url})

        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Terapkan limit jika diminta (ambil chapter terbaru)
        if limit_ch:
            ch_list = ch_list[:limit_ch]

        # Balik urutan menjadi terlama -> terbaru
        ch_list.reverse()

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

        result = {
            "judul": judul,
            "thumb": thumb_cloud if save else thumb_url,
            "source": "arenascan",
            "chapters": final_chapters
        }

        return result

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

# ================== FUNGSI KATALOG ==================
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

def run_catalog_mode(max_pages=8, limit_ch=3):
    """Menjalankan scraping katalog dari kedua sumber."""
    print("=== SCRAPING KATALOG MANHUAPLUS ===")
    manga_list_manhuaplus = scrape_manhuaplus_catalog(max_pages=max_pages)
    for manga in manga_list_manhuaplus:
        slug = manga['slug']
        merged_names = get_merged_chapter_list(slug)
        online_count = len(merged_names)
        chs_string = ", ".join(merged_names)

        result = process_comic_manhuaplus(
            judul=manga['judul'],
            link=manga['url'],
            slug=slug,
            thumb_url=manga['thumb'],
            limit_ch=limit_ch,
            save=False
        )
        if result:
            result['online'] = online_count
            result['Chs'] = chs_string
            # Simpan dengan merge
            save_to_db(slug, result)
            generate_missing_report(slug, merged_names, result['chapters'])
        time.sleep(2)

    print("\n=== SCRAPING KATALOG ARENASCAN ===")
    manga_list_arenascan = scrape_arenascan_catalog(max_pages=max_pages)
    for manga in manga_list_arenascan:
        slug = manga['slug']
        merged_names = get_merged_chapter_list(slug)
        online_count = len(merged_names)
        chs_string = ", ".join(merged_names)

        result = process_comic_arenascan(
            judul=manga['judul'],
            link=manga['url'],
            slug=slug,
            thumb_url=manga['thumb'],
            limit_ch=limit_ch,
            save=False
        )
        if result:
            result['online'] = online_count
            result['Chs'] = chs_string
            save_to_db(slug, result)
            generate_missing_report(slug, merged_names, result['chapters'])
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

# ================== FUNGSI PERBANDINGAN & MERGE (MODE AUTO) ==================
def compare_and_merge_sources(slug):
    """Ambil data dari kedua sumber, periksa kesehatan, gabungkan, dan simpan dengan informasi source_chapter."""
    print(f"\n=== MEMBANDINGKAN DAN MENGGABUNGKAN {slug} ===")
    
    merged_names = get_merged_chapter_list(slug)
    online_count = len(merged_names)
    chs_string = ", ".join(merged_names)

    data_manhua = process_comic_manhuaplus(
        judul=slug.replace('-', ' ').title(),
        link=f"https://manhuaplus.org/manga/{slug}",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False
    )
    data_arena = process_comic_arenascan(
        judul=slug.replace('-', ' ').title(),
        link=f"https://arenascan.com/manga/{slug}/",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False
    )

    # Jika kedua sumber gagal
    if not data_manhua and not data_arena:
        print(f"Gagal mengambil data untuk {slug} dari kedua sumber.")
        return

    # Jika hanya satu sumber berhasil
    if not data_manhua:
        print("Hanya data dari arenascan tersedia, menyimpan...")
        for ch in data_arena.get('chapters', []):
            ch['source_chapter'] = 'arenascan'
        data_arena['online'] = online_count
        data_arena['Chs'] = chs_string
        save_to_db(slug, data_arena)
        compare_sources(slug)
        generate_missing_report(slug, merged_names, data_arena['chapters'])
        return
    if not data_arena:
        print("Hanya data dari manhuaplus tersedia, menyimpan...")
        for ch in data_manhua.get('chapters', []):
            ch['source_chapter'] = 'manhuaplus'
        data_manhua['online'] = online_count
        data_manhua['Chs'] = chs_string
        save_to_db(slug, data_manhua)
        compare_sources(slug)
        generate_missing_report(slug, merged_names, data_manhua['chapters'])
        return

    # Kedua sumber berhasil, lakukan penggabungan dengan pemeriksaan kesehatan
    chapters_manhua = {}
    for ch in data_manhua.get('chapters', []):
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            chapters_manhua[num] = ch

    chapters_arena = {}
    for ch in data_arena.get('chapters', []):
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            chapters_arena[num] = ch

    all_nums = sorted(set(chapters_manhua.keys()) | set(chapters_arena.keys()))
    merged_chapters = []

    for num in all_nums:
        ch_m = chapters_manhua.get(num)
        ch_a = chapters_arena.get(num)
        keep = None
        source_used = None

        if ch_m and ch_a:
            health_m = check_chapter_health(ch_m)
            health_a = check_chapter_health(ch_a)
            if health_m and not health_a:
                keep = ch_m
                source_used = "manhuaplus"
                print(f"  Chapter {num}: menggunakan manhuaplus (arenascan rusak)")
            elif not health_m and health_a:
                keep = ch_a
                source_used = "arenascan"
                print(f"  Chapter {num}: menggunakan arenascan (manhuaplus rusak)")
            elif health_m and health_a:
                keep = ch_m
                source_used = "manhuaplus"
                print(f"  Chapter {num}: kedua sehat, memilih manhuaplus")
            else:
                keep = ch_m
                source_used = "manhuaplus"
                print(f"  Chapter {num}: KEDUA RUSAK, memilih manhuaplus")
        elif ch_m:
            health = check_chapter_health(ch_m)
            keep = ch_m
            source_used = "manhuaplus"
            if not health:
                print(f"  Chapter {num}: hanya di manhuaplus, namun RUSAK")
            else:
                print(f"  Chapter {num}: hanya di manhuaplus (sehat)")
        else:
            health = check_chapter_health(ch_a)
            keep = ch_a
            source_used = "arenascan"
            if not health:
                print(f"  Chapter {num}: hanya di arenascan, namun RUSAK")
            else:
                print(f"  Chapter {num}: hanya di arenascan (sehat)")

        if keep:
            keep['source_chapter'] = source_used
            merged_chapters.append(keep)

    thumb = data_manhua.get('thumb') or data_arena.get('thumb')
    judul = data_manhua.get('judul') or data_arena.get('judul')

    merged_data = {
        "judul": judul,
        "thumb": thumb,
        "source": "merged",
        "online": online_count,
        "Chs": chs_string,
        "chapters": merged_chapters
    }

    save_to_db(slug, merged_data)
    print(f"Data gabungan tersimpan di db/{slug}.json (total {len(merged_chapters)} chapter)")

    compare_sources(slug)
    generate_missing_report(slug, merged_names, merged_chapters)

# ================== FUNGSI LAPORAN PERBANDINGAN ==================
def compare_sources(slug):
    """Bandingkan data dari manhuaplus dan arenascan untuk slug tertentu (tanpa simpan) dan simpan laporan di cp/."""
    print(f"\n=== MEMBUAT LAPORAN PERBANDINGAN {slug} ===")
    data_manhua = process_comic_manhuaplus(
        judul=slug.replace('-', ' ').title(),
        link=f"https://manhuaplus.org/manga/{slug}",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False
    )
    data_arena = process_comic_arenascan(
        judul=slug.replace('-', ' ').title(),
        link=f"https://arenascan.com/manga/{slug}/",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False
    )

    if not data_manhua and not data_arena:
        print("Gagal mengambil dari kedua sumber.")
        return

    def get_chapter_set(data):
        return {extract_chapter_number(ch['nama']) for ch in data.get('chapters', []) if extract_chapter_number(ch['nama']) is not None}

    set_a = get_chapter_set(data_manhua) if data_manhua else set()
    set_b = get_chapter_set(data_arena) if data_arena else set()

    only_a = set_a - set_b
    only_b = set_b - set_a
    common = set_a & set_b

    os.makedirs('cp', exist_ok=True)
    report = {
        'slug': slug,
        'manhuaplus': {
            'judul': data_manhua.get('judul') if data_manhua else None,
            'thumb': data_manhua.get('thumb') if data_manhua else None,
            'total_chapters': len(set_a),
            'chapters': data_manhua.get('chapters', []) if data_manhua else []
        },
        'arenascan': {
            'judul': data_arena.get('judul') if data_arena else None,
            'thumb': data_arena.get('thumb') if data_arena else None,
            'total_chapters': len(set_b),
            'chapters': data_arena.get('chapters', []) if data_arena else []
        },
        'comparison': {
            'only_in_manhuaplus': sorted(list(only_a)),
            'only_in_arenascan': sorted(list(only_b)),
            'common': sorted(list(common))
        }
    }
    report_filename = os.path.join('cp', f'compare_{slug}.json')
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"Laporan perbandingan tersimpan di {report_filename}")

# ================== FUNGSI LAPORAN MISSING ==================
def generate_missing_report(slug, online_names, downloaded_chapters):
    """
    Membandingkan daftar chapter online (online_names) dengan chapter yang berhasil di-download (downloaded_chapters)
    dan menyimpan laporan ke missing.json di root.
    """
    downloaded_names = [ch['nama'] for ch in downloaded_chapters]
    missing = [name for name in online_names if name not in downloaded_names]

    if not missing:
        return  # Tidak ada missing, tidak perlu simpan laporan

    # Baca atau buat file missing.json
    missing_file = 'missing.json'
    if os.path.exists(missing_file):
        with open(missing_file, 'r', encoding='utf-8') as f:
            all_reports = json.load(f)
    else:
        all_reports = []

    # Cari apakah sudah ada laporan untuk slug ini
    existing = next((r for r in all_reports if r['slug'] == slug), None)
    if existing:
        existing['missing'] = missing
        existing['total_online'] = len(online_names)
        existing['total_downloaded'] = len(downloaded_names)
    else:
        all_reports.append({
            'slug': slug,
            'judul': downloaded_chapters[0].get('judul', slug) if downloaded_chapters else slug,
            'total_online': len(online_names),
            'total_downloaded': len(downloaded_names),
            'missing': missing
        })

    with open(missing_file, 'w', encoding='utf-8') as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)
    print(f"Laporan missing diperbarui di {missing_file}")

# ================== MAIN ==================
def main():
    parser = argparse.ArgumentParser(description='Scrape komik dari manhuaplus.org dan arenascan.com')
    parser.add_argument('--slug', help='Slug komik (contoh: nama-komik)')
    parser.add_argument('--source', choices=['manhuaplus', 'arenascan', 'auto'], default='auto',
                        help='Sumber data (default auto: gabungkan kedua sumber)')
    parser.add_argument('--catalog', action='store_true', help='Jalankan mode katalog (mengabaikan slug)')
    parser.add_argument('--pages', type=int, default=8, help='Jumlah halaman katalog (default 8)')
    parser.add_argument('--limit', type=int, default=3, help='Jumlah chapter terbaru yang diambil di mode katalog (default 3)')
    parser.add_argument('--compare', action='store_true', help='Bandingkan data dari dua sumber untuk slug tertentu (tanpa simpan)')
    parser.add_argument('--missing', action='store_true', help='Periksa chapter yang hilang di data lokal dibandingkan dengan online')
    parser.add_argument('--all', action='store_true', help='Gunakan bersama --missing untuk memeriksa semua komik di folder db/')
    args = parser.parse_args()

    if args.missing:
        # Untuk mode missing, kita bisa panggil fungsi terpisah atau gunakan generate_missing_report untuk semua slug
        # Untuk sementara, beri pesan
        print("Mode missing belum diimplementasikan di sini. Gunakan script terpisah.")
        return

    if args.compare:
        if not args.slug:
            print("Slug diperlukan untuk mode compare")
            return
        compare_sources(args.slug)
        return

    if args.catalog:
        run_catalog_mode(max_pages=args.pages, limit_ch=args.limit)
        return

    if args.slug:
        if args.source == 'auto':
            compare_and_merge_sources(args.slug)
        elif args.source == 'manhuaplus':
            merged_names = get_merged_chapter_list(args.slug)
            online_count = len(merged_names)
            chs_string = ", ".join(merged_names)
            result = process_comic_manhuaplus(
                judul=args.slug.replace('-', ' ').title(),
                link=f"https://manhuaplus.org/manga/{args.slug}",
                slug=args.slug,
                thumb_url=None,
                limit_ch=None,
                save=False
            )
            if result:
                result['online'] = online_count
                result['Chs'] = chs_string
                save_to_db(args.slug, result)
                generate_missing_report(args.slug, merged_names, result['chapters'])
        else:  # arenascan
            merged_names = get_merged_chapter_list(args.slug)
            online_count = len(merged_names)
            chs_string = ", ".join(merged_names)
            result = process_comic_arenascan(
                judul=args.slug.replace('-', ' ').title(),
                link=f"https://arenascan.com/manga/{args.slug}/",
                slug=args.slug,
                thumb_url=None,
                limit_ch=None,
                save=False
            )
            if result:
                result['online'] = online_count
                result['Chs'] = chs_string
                save_to_db(args.slug, result)
                generate_missing_report(args.slug, merged_names, result['chapters'])
        return

    # Jika tidak ada argumen, gunakan environment variables
    target_slug = os.environ.get('TARGET_SLUG')
    source = os.environ.get('SOURCE', 'manhuaplus').lower()
    if target_slug:
        if source == 'manhuaplus':
            merged_names = get_merged_chapter_list(target_slug)
            online_count = len(merged_names)
            chs_string = ", ".join(merged_names)
            result = process_comic_manhuaplus(
                judul=target_slug.replace('-', ' ').title(),
                link=f"https://manhuaplus.org/manga/{target_slug}",
                slug=target_slug,
                thumb_url=None,
                limit_ch=None,
                save=False
            )
            if result:
                result['online'] = online_count
                result['Chs'] = chs_string
                save_to_db(target_slug, result)
                generate_missing_report(target_slug, merged_names, result['chapters'])
        elif source == 'arenascan':
            merged_names = get_merged_chapter_list(target_slug)
            online_count = len(merged_names)
            chs_string = ", ".join(merged_names)
            result = process_comic_arenascan(
                judul=target_slug.replace('-', ' ').title(),
                link=f"https://arenascan.com/manga/{target_slug}/",
                slug=target_slug,
                thumb_url=None,
                limit_ch=None,
                save=False
            )
            if result:
                result['online'] = online_count
                result['Chs'] = chs_string
                save_to_db(target_slug, result)
                generate_missing_report(target_slug, merged_names, result['chapters'])
        else:
            print(f"Source tidak dikenal: {source}. Gunakan 'manhuaplus' atau 'arenascan'.")
    else:
        run_catalog_mode(max_pages=8, limit_ch=3)

if __name__ == "__main__":
    main()
