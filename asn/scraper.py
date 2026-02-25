import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

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

# ================== FUNGSI BANTU ==================
def merge_chapters(old_chapters, new_chapters):
    """
    Menggabungkan dua daftar chapter berdasarkan URL.
    Chapter baru akan menimpa yang lama jika URL sama (untuk update).
    Hanya chapter yang memiliki 'url' yang diproses.
    Hasil diurutkan berdasarkan nomor chapter (diekstrak dari nama).
    """
    # Filter chapter yang memiliki url
    old_valid = [ch for ch in old_chapters if 'url' in ch]
    new_valid = [ch for ch in new_chapters if 'url' in ch]

    combined = {ch['url']: ch for ch in old_valid}
    for ch in new_valid:
        combined[ch['url']] = ch  # timpa jika sudah ada
    merged = list(combined.values())

    # Fungsi untuk mengekstrak nomor chapter dari nama (misal "Chapter 41" -> 41.0)
    def get_chapter_number(ch):
        match = re.search(r'(\d+(?:\.\d+)?)', ch['nama'])
        return float(match.group(1)) if match else 0

    merged.sort(key=get_chapter_number)
    return merged

def get_images(chapter_url):
    """Mengambil semua URL gambar dari halaman chapter."""
    try:
        # 1. Ekstrak Chapter ID dari URL
        chapter_id = chapter_url.strip('/').split('/')[-1]

        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match:
                chapter_id = match.group(1)
            else:
                return []

        # 2. Ambil data gambar via AJAX POST
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)

        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']

                # Ambil link dari cdn.manhuaplus.cc lewat Regex
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)

                # Saring link (hapus loading.gif dan duplikat)
                temp_list = []
                seen = set()
                for img in list_gambar:
                    img = img.strip()
                    if "loading.gif" not in img and img not in seen:
                        temp_list.append(img)
                        seen.add(img)

                # Urutkan berdasarkan timestamp nama file
                temp_list.sort()
                return temp_list
        return []
    except Exception as e:
        print(f"Error get_images: {e}")
        return []

def process_comic(judul, link, slug, thumb_url=None, limit_ch=None):
    """
    Memproses satu komik:
    - Mengambil daftar chapter dari halaman detail
    - Mengambil gambar setiap chapter (jika limit_ch ditentukan, hanya limit chapter terbaru)
    - Menggabungkan dengan data lama jika file sudah ada dan valid
    - Menyimpan ke db/{slug}.json
    """
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # --- AMBIL JUDUL ASLI DARI HALAMAN (jika ada) ---
        h1 = soup.select_one('h1')
        if h1:
            judul_asli = h1.get_text(strip=True)
            if judul_asli:
                judul = judul_asli

        # --- AMBIL THUMBNAIL JIKA BELUM ADA ---
        if not thumb_url:
            # Coba meta og:image
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                thumb_url = og_img['content']
            else:
                # Cari gambar lain di area summary
                img_tag = soup.select_one('.summary_image img, .thumb img')
                if img_tag:
                    thumb_url = img_tag.get('src') or img_tag.get('data-src')
                if thumb_url and not thumb_url.startswith('http'):
                    thumb_url = 'https://manhuaplus.org' + thumb_url

        # Upload Sampul ke Cloudinary
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            try:
                up = cloudinary.uploader.upload(
                    thumb_url,
                    public_id=slug,
                    folder="petomic_thumbs",
                    overwrite=True
                )
                thumb_cloud = up['secure_url']
            except Exception as e:
                print(f"Cloudinary upload gagal: {e}")
                thumb_cloud = thumb_url  # Fallback

        # --- AMBIL DAFTAR CHAPTER ---
        ch_list = []

        # Metode utama: dari <ul id="myUL">
        ul_chapter = soup.select_one('ul#myUL')
        if ul_chapter:
            for li in ul_chapter.select('li.chapter'):
                a = li.select_one('a')
                if a and a.get('href'):
                    url = a['href']
                    nama = a.get_text(strip=True)
                    if not nama:
                        nama = li.get('data', '')
                    ch_list.append({"nama": nama, "url": url})

        # Cadangan 1: JSON-LD
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

        # Cadangan 2: Dropdown
        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})

        if not ch_list:
            print(f"Tidak ada chapter ditemukan untuk {slug}")
            return None

        # Terapkan limit jika diminta (hanya untuk katalog)
        if limit_ch:
            ch_list = ch_list[:limit_ch]

        # Ambil gambar untuk setiap chapter
        final_chapters = []
        for ch in ch_list:
            print(f"   -> Scraping Chapter: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "url": ch['url'], "images": imgs})
            time.sleep(0.8)  # Jeda agar tidak kena blokir

        if not final_chapters:
            print(f"Tidak ada gambar berhasil diambil untuk {slug}")
            return None

        # Urutan baca: dari terlama ke terbaru (sesuai permintaan)
        final_chapters.reverse()

        # --- GABUNGKAN DENGAN DATA LAMA (JIKA ADA DAN VALID) ---
        db_path = f'db/{slug}.json'
        if os.path.exists(db_path):
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                old_chapters = old_data.get('chapters', [])
                # Validasi: pastikan setiap chapter punya 'url', jika tidak, anggap file corrupt
                if all(isinstance(ch, dict) and 'url' in ch for ch in old_chapters):
                    final_chapters = merge_chapters(old_chapters, final_chapters)
                    print(f"   -> Menggabungkan dengan {len(old_chapters)} chapter lama")
                else:
                    print(f"   -> File lama tidak valid (ada chapter tanpa url), akan ditimpa dengan data baru")
            except Exception as e:
                print(f"   -> Gagal membaca file lama ({e}), akan menimpa dengan data baru")

        # Simpan hasil
        os.makedirs('db', exist_ok=True)
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump({
                "judul": judul,
                "thumb": thumb_cloud,
                "chapters": final_chapters
            }, f, indent=4)

        print(f"SUKSES: {slug}.json tersimpan (total {len(final_chapters)} chapter).")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}

    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

# ================== MAIN (EKSEKUSI) ==================
def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        # Mode satu slug (full chapters)
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(
            judul=target_slug.replace('-', ' ').title(),
            link=url,
            slug=target_slug,
            thumb_url=None,
            limit_ch=None
        )
    else:
        # Mode katalog: ambil dari halaman 1-10 (bisa disesuaikan)
        print("Scraping katalog rutin PetoMic (Halaman 1-10)...")
        list_json = []

        for page in range(1, 4):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"

            print(f"\n[!] Membuka halaman: {url_katalog}")
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')

            items = soup.select('div.mh-77vh > div, .page-item-detail, .listupd .bs')
            if not items:
                print("Halaman kosong atau selector berubah.")
                break

            print(f"Menemukan {len(items)} judul komik. Memulai proses...")

            for item in items:
                try:
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

                    # Untuk katalog: batasi 2 chapter terbaru (bisa diubah sesuai kebutuhan)
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=3)
                    if hasil:
                        list_json.append(hasil)
                except Exception as e:
                    print(f"Skip item karena error: {e}")
                    continue

        # Simpan katalog utama (list.json)
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"\n--- SELESAI: Total {len(list_json)} komik masuk katalog ---")

if __name__ == "__main__":
    main()
