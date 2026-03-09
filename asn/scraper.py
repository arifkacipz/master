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
import datetime  # <-- tambahan untuk timestamp

# ================== SELENIUM ==================
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

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

def load_existing_chapter_numbers(slug):
    """Mengembalikan set nomor chapter yang sudah ada di file db/{slug}.json."""
    path = f'db/{slug}.json'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            chapters = data.get('chapters', [])
            existing_nums = set()
            for ch in chapters:
                num = extract_chapter_number(ch.get('nama', ''))
                if num is not None:
                    existing_nums.add(num)
            return existing_nums
        except Exception as e:
            print(f"Error membaca file existing {path}: {e}")
            return set()
    return set()

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
    Field `online`, `chapterCount`, dan `Chs` akan diperbarui sesuai nilai di new_data.
    Field `last_scraped` diupdate **hanya jika ada chapter baru yang ditambahkan**.
    """
    os.makedirs('db', exist_ok=True)
    path = f'db/{slug}.json'

    old_data = load_from_db(slug)
    if old_data:
        # Gabungkan chapter
        old_chapters = old_data.get('chapters', [])
        new_chapters = new_data.get('chapters', [])
        merged_chapters = merge_chapters_by_number(old_chapters, new_chapters)
        # Hitung ulang chapterCount berdasarkan chapter yang benar-benar ada (dengan gambar)
        chapterCount = len(merged_chapters)
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
            "chapterCount": chapterCount,
            "Chs": chs,
            "chapters": merged_chapters
        }
        # Tentukan apakah ada chapter baru yang berhasil ditambahkan
        has_new_chapters = len(new_chapters) > 0
        if has_new_chapters:
            final_data['last_scraped'] = datetime.datetime.now().isoformat()
        else:
            # Pertahankan timestamp lama jika ada
            if 'last_scraped' in old_data:
                final_data['last_scraped'] = old_data['last_scraped']
            else:
                # Jika belum ada sama sekali (komik lama upgrade) dan tidak ada chapter baru, jangan tambahkan
                # Biarkan tanpa field last_scraped
                pass
    else:
        # Komik baru – pasti ada chapter baru (karena new_data hanya dibuat jika ada chapter)
        final_data = new_data
        final_data['last_scraped'] = datetime.datetime.now().isoformat()

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4)

def get_headers_for_url(url, default_headers=None):
    """
    Mengembalikan headers yang sesuai untuk URL tertentu.
    Untuk domain WordPress, header Referer dihapus karena dapat memicu blokade.
    """
    if default_headers is None:
        default_headers = HEADERS.copy()
    # Deteksi domain WordPress
    if 'wordpress.com' in url or 'wp.com' in url:
        headers = default_headers.copy()
        headers.pop('Referer', None)
        return headers
    return default_headers

def check_image_url(url):
    """
    Periksa apakah URL gambar dapat diakses dengan GET request (stream=True).
    Gunakan headers yang sesuai berdasarkan domain.
    """
    headers = get_headers_for_url(url)
    try:
        r = requests.get(url, headers=headers, timeout=10, stream=True)
        if r.status_code == 200:
            return True
        else:
            if 'wordpress.com' in url or 'wp.com' in url:
                minimal_headers = {'User-Agent': HEADERS['User-Agent']}
                r2 = requests.get(url, headers=minimal_headers, timeout=10, stream=True)
                return r2.status_code == 200
            return False
    except Exception as e:
        print(f"   [Health Check Error] {e}")
        return False

def check_chapter_health(chapter):
    """Periksa kesehatan chapter dengan mengecek gambar pertama."""
    images = chapter.get('images', [])
    if not images:
        return False
    return check_image_url(images[0])

# ================== FUNGSI AMBIL GAMBAR CHAPTER DENGAN SELENIUM ==================
def get_images_manhuaplus_with_selenium(chapter_url):
    """
    Menggunakan Selenium untuk memuat halaman chapter sepenuhnya,
    lalu mengekstrak semua URL gambar dari elemen <a class="readImg"> dan <img>.
    """
    if not SELENIUM_AVAILABLE:
        print("   Selenium tidak terinstall. Install dengan: pip install selenium")
        return []

    print("   [Selenium] Memuat halaman...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(chapter_url)

        # Tunggu hingga elemen chapterContent muncul (maks 15 detik)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "chapterContent"))
            )
        except:
            pass  # tetap lanjutkan, mungkin tidak ada ID itu

        # Beri waktu ekstra untuk gambar-gambar yang dimuat secara lambat
        time.sleep(3)

        # Cari semua elemen a dengan class readImg (href)
        links = driver.find_elements(By.CSS_SELECTOR, "a.readImg")
        urls = []
        for a in links:
            href = a.get_attribute("href")
            if href and href.startswith("http") and "loading.gif" not in href:
                urls.append(href)

        # Jika tidak ada, cari semua elemen img
        if not urls:
            imgs = driver.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and src.startswith("http") and "loading.gif" not in src and ".svg" not in src:
                    urls.append(src)

        # Hapus duplikat
        seen = set()
        unique = []
        for url in urls:
            if url not in seen:
                unique.append(url)
                seen.add(url)

        print(f"   [Selenium] Ditemukan {len(unique)} URL gambar.")
        return unique

    except Exception as e:
        print(f"   [Selenium Error] {e}")
        return []
    finally:
        if driver:
            driver.quit()

# ================== FUNGSI AMBIL GAMBAR CHAPTER (MANHUAPLUS) ==================
def get_images_manhuaplus(chapter_url, use_selenium=False):
    """
    Mengambil semua URL gambar dari halaman chapter manhuaplus.
    Prioritas:
    1. Menggunakan endpoint AJAX.
    2. Jika gagal, parsing langsung halaman HTML dari div#chapterContent (fallback).
    3. Jika masih kosong dan use_selenium=True, gunakan Selenium.
    """
    images = []

    # --- METODE 1: AJAX ---
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match:
                chapter_id = match.group(1)
            else:
                print("   Tidak dapat menemukan CHAPTER_ID.")

        if chapter_id.isdigit():
            ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
            ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
            if ajax_res.status_code == 200:
                data = ajax_res.json()
                if data.get('status') and 'html' in data:
                    html_content = data['html']
                    soup = BeautifulSoup(html_content, 'html.parser')
                    # Cari gambar dari tag img
                    for img in soup.find_all('img'):
                        src = img.get('src')
                        if src and src.startswith('http') and 'loading.gif' not in src:
                            images.append(src)
                    # Juga cari dari a.readImg (href)
                    for a in soup.find_all('a', class_='readImg'):
                        href = a.get('href')
                        if href and href.startswith('http') and 'loading.gif' not in href:
                            images.append(href)
                    # Hapus duplikat
                    seen = set()
                    temp_list = []
                    for img in images:
                        if img not in seen:
                            temp_list.append(img)
                            seen.add(img)
                    if temp_list:
                        print(f"   [AJAX] Ditemukan {len(temp_list)} gambar.")
                        # Jika gambar pertama gagal, coba Selenium
                        if use_selenium and not check_image_url(temp_list[0]):
                            print("   Gambar pertama AJAX gagal, mencoba Selenium...")
                            selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
                            if selenium_imgs:
                                return selenium_imgs
                        return temp_list
            print("   Metode AJAX gagal.")
    except Exception as e:
        print(f"   Error AJAX: {e}")

    # --- METODE 2: Fallback HTML (div#chapterContent) ---
    try:
        fallback_images = get_images_manhuaplus_fallback(chapter_url)
        if fallback_images:
            print(f"   [Fallback] Ditemukan {len(fallback_images)} gambar.")
            # Jika gambar pertama gagal, coba Selenium
            if use_selenium and not check_image_url(fallback_images[0]):
                print("   Gambar pertama fallback gagal, mencoba Selenium...")
                selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
                if selenium_imgs:
                    return selenium_imgs
            return fallback_images
    except Exception as e:
        print(f"   Error fallback HTML: {e}")

    # --- METODE 3: Selenium (jika masih kosong dan diaktifkan) ---
    if use_selenium:
        print("   Tidak ada gambar dari metode sebelumnya, mencoba Selenium...")
        selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
        if selenium_imgs:
            return selenium_imgs
        else:
            print("   Selenium tidak menemukan gambar.")
    else:
        print("   Selenium tidak diaktifkan (gunakan --selenium untuk mengaktifkan).")

    return []

def get_images_manhuaplus_fallback(chapter_url):
    """
    Fallback sederhana: ambil semua gambar dari div#chapterContent tanpa filter domain.
    Hanya mengecualikan loading.gif dan file .svg.
    """
    try:
        res = requests.get(chapter_url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"   Gagal mengakses {chapter_url} (status {res.status_code})")
            return []
        soup = BeautifulSoup(res.text, 'html.parser')
        chapter_content = soup.find('div', id='chapterContent')
        if not chapter_content:
            print(f"   Tidak menemukan div#chapterContent")
            return []
        images = []
        for img in chapter_content.find_all('img'):
            src = img.get('src')
            if src and src.startswith('http') and 'loading.gif' not in src and '.svg' not in src:
                images.append(src)
        return images
    except Exception as e:
        print(f"Error get_images_manhuaplus_fallback: {e}")
        return []

def get_images_arenascan(chapter_url):
    """Ambil semua URL gambar dari halaman chapter arenascan (tetap sama)."""
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

# ================== FUNGSI MEMPROSES SATU SUMBER ==================
def process_comic_manhuaplus(judul, link, slug, thumb_url=None, limit_ch=None, save=True, return_all=False, use_selenium=False):
    """
    Memproses satu komik dari manhuaplus.
    Hanya mengambil chapter yang belum ada di file db/{slug}.json.
    Semua chapter yang memiliki daftar gambar akan disimpan, meskipun gambar pertama tidak bisa diakses.
    """
    print(f"--- ManhuaPlus memproses: {judul} ---")
    try:
        # Load chapter yang sudah ada
        existing_nums = load_existing_chapter_numbers(slug)
        print(f"   Chapter sudah ada di db: {len(existing_nums)}")

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

        # Ambil daftar chapter (lengkap)
        ch_list = []
        ul_chapter = soup.select_one('ul#myUL')
        if ul_chapter:
            for li in ul_chapter.select('li.chapter'):
                a = li.select_one('a')
                if a and a.get('href'):
                    url = a['href']
                    nama = a.get_text(strip=True) or li.get('data', '')
                    ch_list.append({"nama": nama, "url": url})

        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Semua nama chapter (untuk online count)
        all_chapters = [ch['nama'] for ch in ch_list]

        # Filter chapter yang belum ada di db
        ch_to_scrape = []
        for ch in ch_list:
            num = extract_chapter_number(ch['nama'])
            if num is None or num not in existing_nums:
                ch_to_scrape.append(ch)
            # Tidak menampilkan setiap chapter yang dilewati

        skipped = len(ch_list) - len(ch_to_scrape)
        print(f"   {skipped} Chapter dilewati.")
        print(f"   Chapter baru ditemukan: {len(ch_to_scrape)}")

        # Urutkan ascending lalu ambil chapter terbaru (nomor terbesar)
        if ch_to_scrape:
            ch_to_scrape.sort(key=lambda x: extract_chapter_number(x['nama']) or 0)  # ascending
            if limit_ch:
                ch_to_scrape = ch_to_scrape[-limit_ch:]   # ambil chapter dengan nomor terbesar

        # Ambil gambar setiap chapter baru
        healthy_chapters = []
        for ch in ch_to_scrape:
            print(f"   -> Scraping Chapter baru: {ch['nama']}")
            imgs = get_images_manhuaplus(ch['url'], use_selenium=use_selenium)
            if imgs:
                # Lakukan health check untuk informasi, tetap simpan meskipun gagal
                if check_image_url(imgs[0]):
                    print(f"      [✓] Gambar pertama OK.")
                else:
                    print(f"      [⚠️] Gambar pertama gagal diakses, tetapi tetap disimpan.")
                healthy_chapters.append({"nama": ch['nama'], "url": ch['url'], "images": imgs})
            else:
                print(f"      [⚠️] Chapter {ch['nama']} tidak memiliki gambar, dilewati.")
            time.sleep(0.8)

        if not healthy_chapters and not return_all:
            print(f"Tidak ada chapter baru yang sehat untuk {slug}")
            return None

        if return_all:
            return (healthy_chapters, all_chapters, judul, thumb_cloud if save else thumb_url)
        else:
            result = {
                "judul": judul,
                "thumb": thumb_cloud if save else thumb_url,
                "source": "manhuaplus",
                "online": len(all_chapters),
                "chapterCount": len(healthy_chapters),
                "Chs": ", ".join(all_chapters),
                "chapters": healthy_chapters
            }
            return result

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def process_comic_arenascan(judul, link, slug, thumb_url=None, limit_ch=None, save=True, return_all=False):
    """
    Memproses satu komik dari arenascan.
    Hanya mengambil chapter yang belum ada di file db/{slug}.json.
    """
    print(f"--- Arenascan memproses: {judul} ---")
    try:
        existing_nums = load_existing_chapter_numbers(slug)
        print(f"   Chapter sudah ada di db: {len(existing_nums)}")

        res = requests.get(link, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"Gagal mengakses {link}, status code: {res.status_code}")
            return None
        soup = BeautifulSoup(res.text, 'html.parser')

        h1 = soup.select_one('h1.entry-title')
        if h1:
            judul = h1.get_text(strip=True)

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

        all_chapters = [ch['nama'] for ch in ch_list]

        # Filter chapter yang belum ada di db
        ch_to_scrape = []
        for ch in ch_list:
            num = extract_chapter_number(ch['nama'])
            if num is None or num not in existing_nums:
                ch_to_scrape.append(ch)
            # Tidak menampilkan setiap chapter yang dilewati

        skipped = len(ch_list) - len(ch_to_scrape)
        print(f"   {skipped} Chapter dilewati.")
        print(f"   Chapter baru ditemukan: {len(ch_to_scrape)}")

        # Urutkan ascending lalu ambil chapter terbaru
        if ch_to_scrape:
            ch_to_scrape.sort(key=lambda x: extract_chapter_number(x['nama']) or 0)
            if limit_ch:
                ch_to_scrape = ch_to_scrape[-limit_ch:]

        # Ambil gambar setiap chapter baru
        healthy_chapters = []
        for ch in ch_to_scrape:
            print(f"   -> Scraping Chapter baru: {ch['nama']}")
            imgs = get_images_arenascan(ch['url'])
            if imgs:
                if check_image_url(imgs[0]):
                    print(f"      [✓] Gambar pertama OK.")
                else:
                    print(f"      [⚠️] Gambar pertama gagal diakses, tetapi tetap disimpan.")
                healthy_chapters.append({"nama": ch['nama'], "url": ch['url'], "images": imgs})
            else:
                print(f"      [⚠️] Chapter {ch['nama']} tidak memiliki gambar, dilewati.")
            time.sleep(0.8)

        if not healthy_chapters and not return_all:
            print(f"Tidak ada chapter baru yang sehat untuk {slug}")
            return None

        if return_all:
            return (healthy_chapters, all_chapters, judul, thumb_cloud if save else thumb_url)
        else:
            result = {
                "judul": judul,
                "thumb": thumb_cloud if save else thumb_url,
                "source": "arenascan",
                "online": len(all_chapters),
                "chapterCount": len(healthy_chapters),
                "Chs": ", ".join(all_chapters),
                "chapters": healthy_chapters
            }
            return result
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

# ================== FUNGSI PENGGABUNGAN DUA DATA ==================
def merge_two_comic_data(data1, data2, slug):
    """
    Menggabungkan dua hasil return_all dari process_comic_... untuk slug yang sama.
    data1 dan data2 masing-masing tuple (healthy, all_ch, judul, thumb)
    Mengembalikan dictionary final_data siap simpan.
    """
    healthy1, all_ch1, judul1, thumb1 = data1
    healthy2, all_ch2, judul2, thumb2 = data2

    # Gabungkan semua nama chapter (online) tanpa duplikat berdasarkan nomor
    all_numbers = set()
    all_names = []

    for nama in all_ch1:
        num = extract_chapter_number(nama)
        if num is not None and num not in all_numbers:
            all_numbers.add(num)
            all_names.append(nama)
    for nama in all_ch2:
        num = extract_chapter_number(nama)
        if num is not None and num not in all_numbers:
            all_numbers.add(num)
            all_names.append(nama)

    all_names.sort(key=lambda x: extract_chapter_number(x) or 0)
    online_count = len(all_names)
    chs_string = ", ".join(all_names)

    # Gabungkan chapter sehat berdasarkan nomor, pilih sumber mana yang digunakan
    chapters_by_num = {}
    for ch in healthy1:
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            chapters_by_num[num] = (ch, 'manhuaplus')
    for ch in healthy2:
        num = extract_chapter_number(ch['nama'])
        if num is not None:
            if num not in chapters_by_num:
                chapters_by_num[num] = (ch, 'arenascan')

    merged_chapters = []
    for num in sorted(chapters_by_num.keys()):
        ch, src = chapters_by_num[num]
        ch['source_chapter'] = src
        merged_chapters.append(ch)

    thumb = thumb1 or thumb2
    judul = judul1 or judul2

    final_data = {
        "judul": judul,
        "thumb": thumb,
        "source": "merged",
        "online": online_count,
        "chapterCount": len(merged_chapters),
        "Chs": chs_string,
        "chapters": merged_chapters
    }
    return final_data

# ================== FUNGSI KATALOG ==================
def scrape_manhuaplus_catalog(max_pages=10):
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

def run_catalog_mode(max_pages=8, limit_ch=3, use_selenium=False):
    print("=== SCRAPING KATALOG MANHUAPLUS ===")
    manga_list_manhuaplus = scrape_manhuaplus_catalog(max_pages=max_pages)
    # Kumpulkan hasil sementara dari manhuaplus
    results_manhua = {}
    for manga in manga_list_manhuaplus:
        slug = manga['slug']
        result = process_comic_manhuaplus(
            judul=manga['judul'],
            link=manga['url'],
            slug=slug,
            thumb_url=manga['thumb'],
            limit_ch=limit_ch,
            save=False,           # Jangan simpan dulu
            return_all=True,
            use_selenium=use_selenium
        )
        if result:
            results_manhua[slug] = result
        time.sleep(2)

    print("\n=== SCRAPING KATALOG ARENASCAN ===")
    manga_list_arenascan = scrape_arenascan_catalog(max_pages=max_pages)
    results_arena = {}
    for manga in manga_list_arenascan:
        slug = manga['slug']
        result = process_comic_arenascan(
            judul=manga['judul'],
            link=manga['url'],
            slug=slug,
            thumb_url=manga['thumb'],
            limit_ch=limit_ch,
            save=False,
            return_all=True
        )
        if result:
            results_arena[slug] = result
        time.sleep(2)

    # Gabungkan semua slug dari kedua hasil
    all_slugs = set(results_manhua.keys()) | set(results_arena.keys())

    for slug in all_slugs:
        data_manhua = results_manhua.get(slug)
        data_arena = results_arena.get(slug)

        if data_manhua and data_arena:
            # Gabungkan
            final_data = merge_two_comic_data(data_manhua, data_arena, slug)
            print(f"   {slug}: menggabungkan data dari kedua sumber.")
        elif data_manhua:
            # Hanya dari manhuaplus
            healthy, all_ch, judul, thumb = data_manhua
            online_count = len(all_ch)
            chs_string = ", ".join(all_ch)
            for ch in healthy:
                ch['source_chapter'] = 'manhuaplus'
            final_data = {
                "judul": judul,
                "thumb": thumb,
                "source": "manhuaplus",
                "online": online_count,
                "chapterCount": len(healthy),
                "Chs": chs_string,
                "chapters": healthy
            }
        else:  # hanya dari arenascan
            healthy, all_ch, judul, thumb = data_arena
            online_count = len(all_ch)
            chs_string = ", ".join(all_ch)
            for ch in healthy:
                ch['source_chapter'] = 'arenascan'
            final_data = {
                "judul": judul,
                "thumb": thumb,
                "source": "arenascan",
                "online": online_count,
                "chapterCount": len(healthy),
                "Chs": chs_string,
                "chapters": healthy
            }

        # Simpan ke db (akan digabungkan dengan data lama jika ada)
        save_to_db(slug, final_data)
        # Buat laporan missing (opsional)
        all_ch_names = final_data['Chs'].split(', ') if final_data['Chs'] else []
        generate_missing_report(slug, all_ch_names, final_data['chapters'])

# ================== FUNGSI PERBANDINGAN & MERGE ==================
def compare_and_merge_sources(slug, use_selenium=False):
    print(f"\n=== MEMBANDINGKAN DAN MENGGABUNGKAN {slug} ===")

    data_manhua = process_comic_manhuaplus(
        judul=slug.replace('-', ' ').title(),
        link=f"https://manhuaplus.org/manga/{slug}",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False,
        return_all=True,
        use_selenium=use_selenium
    )
    data_arena = process_comic_arenascan(
        judul=slug.replace('-', ' ').title(),
        link=f"https://arenascan.com/manga/{slug}/",
        slug=slug,
        thumb_url=None,
        limit_ch=None,
        save=False,
        return_all=True
    )

    if not data_manhua and not data_arena:
        print(f"Gagal mengambil data untuk {slug} dari kedua sumber.")
        return

    if data_manhua and data_arena:
        final_data = merge_two_comic_data(data_manhua, data_arena, slug)
    elif data_manhua:
        healthy, all_ch, judul, thumb = data_manhua
        online_count = len(all_ch)
        chs_string = ", ".join(all_ch)
        for ch in healthy:
            ch['source_chapter'] = 'manhuaplus'
        final_data = {
            "judul": judul,
            "thumb": thumb,
            "source": "manhuaplus",
            "online": online_count,
            "chapterCount": len(healthy),
            "Chs": chs_string,
            "chapters": healthy
        }
    else:  # data_arena
        healthy, all_ch, judul, thumb = data_arena
        online_count = len(all_ch)
        chs_string = ", ".join(all_ch)
        for ch in healthy:
            ch['source_chapter'] = 'arenascan'
        final_data = {
            "judul": judul,
            "thumb": thumb,
            "source": "arenascan",
            "online": online_count,
            "chapterCount": len(healthy),
            "Chs": chs_string,
            "chapters": healthy
        }

    save_to_db(slug, final_data)
    print(f"Data tersimpan di db/{slug}.json (total {final_data['chapterCount']} chapter sehat dari {final_data['online']} online)")
    generate_missing_report(slug, final_data['Chs'].split(', '), final_data['chapters'])

# ================== LAPORAN MISSING ==================
def generate_missing_report(slug, online_names, downloaded_chapters):
    # Coba baca file db untuk mendapatkan chapter yang sudah didownload (data terkini)
    db_path = f'db/{slug}.json'
    downloaded_names = []
    judul = slug

    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            downloaded_names = [ch['nama'] for ch in data.get('chapters', [])]
            judul = data.get('judul', slug)
        except Exception as e:
            print(f"Error membaca {db_path}: {e}")
            # Fallback ke parameter jika file corrupt
            downloaded_names = [ch['nama'] for ch in downloaded_chapters]
            if downloaded_chapters:
                judul = downloaded_chapters[0].get('judul', slug)
    else:
        # File belum ada, gunakan parameter (biasanya untuk komik baru)
        downloaded_names = [ch['nama'] for ch in downloaded_chapters]
        if downloaded_chapters:
            judul = downloaded_chapters[0].get('judul', slug)

    missing = [name for name in online_names if name not in downloaded_names]

    missing_file = 'missing.json'
    if os.path.exists(missing_file):
        with open(missing_file, 'r', encoding='utf-8') as f:
            all_reports = json.load(f)
    else:
        all_reports = []

    # Update atau tambah laporan
    updated = False
    for report in all_reports:
        if report.get('slug') == slug:
            report.update({
                'judul': judul,
                'total_online': len(online_names),
                'total_downloaded': len(downloaded_names),
                'missing': missing
            })
            updated = True
            break

    if not updated:
        all_reports.append({
            'slug': slug,
            'judul': judul,
            'total_online': len(online_names),
            'total_downloaded': len(downloaded_names),
            'missing': missing
        })

    # Hanya simpan jika ada missing, jika tidak, hapus dari laporan
    if not missing:
        all_reports = [r for r in all_reports if r.get('slug') != slug]
        print(f"Tidak ada missing untuk {slug}, dihapus dari missing.json.")

    with open(missing_file, 'w', encoding='utf-8') as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)
    print(f"Laporan missing diperbarui di {missing_file}")

# ================== GENERATE LIST (versi scraper) ==================
def generate_list():
    import datetime
    all_manga = []
    for filename in os.listdir('db'):
        if filename.endswith('.json'):
            filepath = os.path.join('db', filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                slug = filename[:-5]
                judul = data.get('judul', slug)
                thumb = data.get('thumb', '')
                last_scraped = data.get('last_scraped')
                if not last_scraped:
                    # Fallback ke waktu modifikasi file untuk komik lama
                    mtime = os.path.getmtime(filepath)
                    last_scraped = datetime.datetime.fromtimestamp(mtime).isoformat()
                all_manga.append({
                    "judul": judul,
                    "slug": slug,
                    "thumb": thumb,
                    "Updated": last_scraped
                })
            except Exception as e:
                print(f"Gagal membaca {filepath}: {e}")
    # Urutkan berdasarkan Updated terbaru
    all_manga.sort(key=lambda x: x["Updated"], reverse=True)
    with open('list.json', 'w', encoding='utf-8') as f:
        json.dump(all_manga, f, indent=4)
    print(f"list.json diperbarui dengan {len(all_manga)} manga.")

# ================== GENERATE STATS ==================
def generate_stats():
    stats = []
    for filename in os.listdir('db'):
        if filename.endswith('.json'):
            with open(os.path.join('db', filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
                slug = filename[:-5]
                judul = data.get("judul", slug)
                thumb = data.get("thumb", "")
                online = data.get("online", len(data.get("chapters", [])))
                chapterCount = data.get("chapterCount", 0)
                chs = data.get("Chs", "")
                source = data.get("source", "unknown")
                stats.append({
                    "slug": slug,
                    "judul": judul,
                    "thumb": thumb,
                    "source": source,
                    "online": online,
                    "chapterCount": chapterCount,
                    "Chs": chs
                })
    low_chapter = [c for c in stats if c['online'] < 15]
    with open('stats.json', 'w', encoding='utf-8') as f:
        json.dump(low_chapter, f, indent=2, ensure_ascii=False)
    print(f"stats.json diperbarui dengan {len(low_chapter)} komik (online < 15).")

# ================== MAIN ==================
def main():
    parser = argparse.ArgumentParser(description='Scrape komik dari manhuaplus.org dan arenascan.com')
    parser.add_argument('--slug', help='Slug komik (contoh: nama-komik)')
    parser.add_argument('--source', choices=['manhuaplus', 'arenascan', 'auto'], default='auto',
                        help='Sumber data (default auto: gabungkan kedua sumber)')
    parser.add_argument('--catalog', action='store_true', help='Jalankan mode katalog')
    parser.add_argument('--pages', type=int, default=8, help='Jumlah halaman katalog (default 8)')
    parser.add_argument('--limit', type=int, default=3, help='Jumlah chapter terbaru (mode katalog)')
    parser.add_argument('--compare', action='store_true', help='Bandingkan dua sumber tanpa simpan')
    parser.add_argument('--generate-list', action='store_true', help='Hasilkan list.json dari db/')
    parser.add_argument('--generate-stats', action='store_true', help='Hasilkan stats.json dari db/')
    parser.add_argument('--selenium', action='store_true', help='Gunakan Selenium jika AJAX dan fallback HTML gagal')
    args = parser.parse_args()

    if args.generate_list:
        generate_list()
        return

    if args.generate_stats:
        generate_stats()
        return

    if args.compare:
        if not args.slug:
            print("Slug diperlukan untuk mode compare")
            return
        print("Fungsi compare_sources belum diimplementasikan.")
        return

    if args.catalog:
        run_catalog_mode(max_pages=args.pages, limit_ch=args.limit, use_selenium=args.selenium)
        generate_list()
        generate_stats()
        return

    if args.slug:
        if args.source == 'auto':
            compare_and_merge_sources(args.slug, use_selenium=args.selenium)
        elif args.source == 'manhuaplus':
            result = process_comic_manhuaplus(
                judul=args.slug.replace('-', ' ').title(),
                link=f"https://manhuaplus.org/manga/{args.slug}",
                slug=args.slug,
                thumb_url=None,
                limit_ch=None,
                save=False,
                return_all=True,
                use_selenium=args.selenium
            )
            if result:
                healthy, all_ch, judul, thumb = result
                online_count = len(all_ch)
                chs_string = ", ".join(all_ch)
                for ch in healthy:
                    ch['source_chapter'] = 'manhuaplus'
                final_data = {
                    "judul": judul,
                    "thumb": thumb,
                    "source": "manhuaplus",
                    "online": online_count,
                    "chapterCount": len(healthy),
                    "Chs": chs_string,
                    "chapters": healthy
                }
                save_to_db(args.slug, final_data)
                generate_missing_report(args.slug, all_ch, healthy)
        else:  # arenascan
            result = process_comic_arenascan(
                judul=args.slug.replace('-', ' ').title(),
                link=f"https://arenascan.com/manga/{args.slug}/",
                slug=args.slug,
                thumb_url=None,
                limit_ch=None,
                save=False,
                return_all=True
            )
            if result:
                healthy, all_ch, judul, thumb = result
                online_count = len(all_ch)
                chs_string = ", ".join(all_ch)
                for ch in healthy:
                    ch['source_chapter'] = 'arenascan'
                final_data = {
                    "judul": judul,
                    "thumb": thumb,
                    "source": "arenascan",
                    "online": online_count,
                    "chapterCount": len(healthy),
                    "Chs": chs_string,
                    "chapters": healthy
                }
                save_to_db(args.slug, final_data)
                generate_missing_report(args.slug, all_ch, healthy)
        generate_list()
        generate_stats()
        return

    # Jika tidak ada argumen, gunakan environment variables
    target_slug = os.environ.get('TARGET_SLUG')
    source = os.environ.get('SOURCE', 'manhuaplus').lower()
    use_selenium = os.environ.get('USE_SELENIUM', 'false').lower() == 'true'
    if target_slug:
        if source == 'manhuaplus':
            result = process_comic_manhuaplus(
                judul=target_slug.replace('-', ' ').title(),
                link=f"https://manhuaplus.org/manga/{target_slug}",
                slug=target_slug,
                thumb_url=None,
                limit_ch=None,
                save=False,
                return_all=True,
                use_selenium=use_selenium
            )
            if result:
                healthy, all_ch, judul, thumb = result
                online_count = len(all_ch)
                chs_string = ", ".join(all_ch)
                for ch in healthy:
                    ch['source_chapter'] = 'manhuaplus'
                final_data = {
                    "judul": judul,
                    "thumb": thumb,
                    "source": "manhuaplus",
                    "online": online_count,
                    "chapterCount": len(healthy),
                    "Chs": chs_string,
                    "chapters": healthy
                }
                save_to_db(target_slug, final_data)
                generate_missing_report(target_slug, all_ch, healthy)
        elif source == 'arenascan':
            result = process_comic_arenascan(
                judul=target_slug.replace('-', ' ').title(),
                link=f"https://arenascan.com/manga/{target_slug}/",
                slug=target_slug,
                thumb_url=None,
                limit_ch=None,
                save=False,
                return_all=True
            )
            if result:
                healthy, all_ch, judul, thumb = result
                online_count = len(all_ch)
                chs_string = ", ".join(all_ch)
                for ch in healthy:
                    ch['source_chapter'] = 'arenascan'
                final_data = {
                    "judul": judul,
                    "thumb": thumb,
                    "source": "arenascan",
                    "online": online_count,
                    "chapterCount": len(healthy),
                    "Chs": chs_string,
                    "chapters": healthy
                }
                save_to_db(target_slug, final_data)
                generate_missing_report(target_slug, all_ch, healthy)
        else:
            print(f"Source tidak dikenal: {source}")
        generate_list()
        generate_stats()
    else:
        run_catalog_mode(max_pages=8, limit_ch=3, use_selenium=use_selenium)
        generate_list()
        generate_stats()

if __name__ == "__main__":
    main()
