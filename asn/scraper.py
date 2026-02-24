import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

# Konfigurasi Cloudinary
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
    except Exception as e:
        print(f"Error get_images: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    # 1. Load Data Lama (Logika Append)
    old_chapters_dict = {}
    old_thumb = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                # Gunakan nama sebagai key agar tidak ada duplikat
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                old_thumb = old_data.get('thumb', '')
        except: pass

    try:
        # 2. Ambil Daftar Chapter (Mencari semua elemen yang mungkin)
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list_from_web = []

        # Selector untuk mengambil seluruh list chapter di ManhuaPlus
        items = soup.select('ul.row-content-chapter li, .eplister li, .cl li')
        for item in items:
            a_tag = item.find('a')
            if a_tag and 'href' in a_tag.attrs:
                u = a_tag['href']
                n = a_tag.text.strip()
                if "/chapters/" in u:
                    ch_list_from_web.append({"nama": n, "url": u})

        # 3. Filter: Mana yang belum ada di database?
        new_chapters_to_scrape = []
        for ch in ch_list_from_web:
            if ch['nama'] not in old_chapters_dict:
                new_chapters_to_scrape.append(ch)

        # Jika sedang update rutin (limit_ch), ambil sedikit saja
        if limit_ch:
            new_chapters_to_scrape = new_chapters_to_scrape[:limit_ch]

        print(f"   [+] Menemukan {len(new_chapters_to_scrape)} chapter baru.")

        # 4. Scrape hanya chapter yang baru
        for ch in new_chapters_to_scrape:
            print(f"   -> Scraping Chapter Baru: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1) # Jeda aman

        # 5. Gabungkan dan Simpan
        # Urutkan berdasarkan nama (asumsi format 'Chapter X')
        all_chapters = list(old_chapters_dict.values())
        
        # Sorting sederhana agar chapter 1 di awal
        try:
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except:
            pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "judul": judul, 
                "thumb": old_thumb or thumb_url, 
                "chapters": all_chapters
            }, f, indent=4)
        
        print(f"SUKSES: {slug}.json diperbarui (Total: {len(all_chapters)} chapter).")
        return {"judul": judul, "slug": slug, "thumb": old_thumb or thumb_url}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        # Logika katalog rutin (Halaman 1 saja untuk update harian)
        # ... (tetap seperti script lama kamu)
