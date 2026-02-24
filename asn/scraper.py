import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

# 1. KONFIGURASI CLOUDINARY
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    """Mengambil daftar gambar dari sebuah chapter menggunakan AJAX."""
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                # Regex untuk mengambil link cdn
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
                temp_list = []
                seen = set()
                for img in list_gambar:
                    img = img.strip()
                    if "loading.gif" not in img and img not in seen:
                        temp_list.append(img)
                        seen.add(img)
                temp_list.sort()
                return temp_list
        return []
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    """Memproses satu judul komik: mengambil daftar chapter lengkap dan scraping gambar."""
    print(f"\n--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    # 1. Load Database Lama (Logika Append)
    old_chapters_dict = {}
    old_thumb = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                old_thumb = old_data.get('thumb', '')
                print(f"   [!] Database ditemukan: {len(old_chapters_dict)} chapter sudah tersimpan.")
        except: pass

    try:
        # 2. Cari Manga ID untuk Request Daftar Chapter Lengkap
        res = requests.get(link, headers=HEADERS, timeout=20)
        m_id_match = re.search(r'manga_id\s*:\s*["\'](\d+)["\']|data-id=["\'](\d+)["\']', res.text)
        
        ch_list_from_web = []
        if m_id_match:
            manga_id = m_id_match.group(1) or m_id_match.group(2)
            print(f"   [+] Manga ID: {manga_id}. Mengambil daftar chapter lengkap via AJAX...")
            
            ajax_ch_url = f"https://manhuaplus.org/ajax/chapters/list?manga_id={manga_id}"
            ajax_ch_res = requests.post(ajax_ch_url, headers=HEADERS, timeout=20)
            
            if ajax_ch_res.status_code == 200:
                soup_ch = BeautifulSoup(ajax_ch_res.text, 'html.parser')
                items = soup_ch.select('li.a-h, li')
                for item in items:
                    a_tag = item.find('a')
                    if a_tag and 'href' in a_tag.attrs:
                        u, n = a_tag['href'], a_tag.text.strip()
                        if "/chapters/" in u:
                            ch_list_from_web.append({"nama": n, "url": u})

        # Backup: Jika AJAX gagal, gunakan selector standar halaman
        if not ch_list_from_web:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('ul.row-content-chapter li, .eplister li, .cl li')
            for item in items:
                a_tag = item.find('a')
                if a_tag: ch_list_from_web.append({"nama": a_tag.text.strip(), "url": a_tag['href']})

        # 3. Filter Chapter Baru & Scrape
        new_chapters = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]
        new_chapters.reverse() # Proses dari chapter terlama yang belum ada

        if limit_ch:
            new_chapters = new_chapters[:limit_ch]

        if not new_chapters:
            print("   [~] Tidak ada chapter baru untuk di-scrape.")
            return {"judul": judul, "slug": slug, "thumb": old_thumb or thumb_url}

        print(f"   [+] Menemukan {len(new_chapters)} chapter baru. Memulai scraping...")

        for ch in new_chapters:
            print(f"   -> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1)

        # 4. Sorting Numerik & Simpan
        all_chapters = list(old_chapters_dict.values())
        try:
            # Mengurutkan berdasarkan angka pertama yang ditemukan di nama chapter (dukungan desimal)
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except: pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": old_thumb or thumb_url, "chapters": all_chapters}, f, indent=4)
        
        print(f"SUKSES: {slug}.json diperbarui. Total: {len(all_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": old_thumb or thumb_url}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    """Fungsi utama untuk menentukan mode scraping (Manual via Slug atau Rutin)."""
    target_slug = os.environ.get('TARGET_SLUG')
    
    if target_slug:
        # MODE MANUAL: Ambil seluruh daftar chapter untuk slug tertentu
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        # MODE RUTIN: Update katalog dari Halaman 1-3
        print("Scraping katalog rutin PetoMic...")
        list_json = []
        for page in range(1, 4):
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update"
            try:
                res = requests.get(url_katalog, headers=HEADERS, timeout=20)
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('.listupd .bs, .page-item-detail, .mh-77vh > div')
                
                for item in items:
                    link_tag = item.select_one('a')
                    if not link_tag: continue
                    judul = link_tag.get('title') or link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.strip('/').split('/')[-1]
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                    
                    # Update rutin hanya mengambil 5 chapter terbaru agar cepat
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
                    if hasil: list_json.append(hasil)
            except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"\nSelesai! {len(list_json)} komik di katalog utama.")

if __name__ == "__main__":
    main()
