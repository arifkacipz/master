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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    try:
        # 1. Ambil halaman chapter untuk mencari CHAPTER_ID
        res = requests.get(chapter_url, headers=HEADERS, timeout=30)
        html = res.text
        
        # Cari CHAPTER_ID menggunakan Regex (Berdasarkan script yang kamu berikan)
        # Contoh di HTML: const CHAPTER_ID = 92929;
        match = re.search(r'const\s+CHAPTER_ID\s*=\s*(\d+)', html)
        if not match:
            print(f"DEBUG: CHAPTER_ID tidak ketemu di {chapter_url}")
            return []
            
        chapter_id = match.group(1)
        print(f"DEBUG: Chapter ID ditemukan: {chapter_id}")

        # 2. Lakukan POST request ke AJAX endpoint (Cara ManhuaPlus memuat gambar)
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=30)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                # Parse HTML yang dikembalikan oleh AJAX
                img_soup = BeautifulSoup(data['html'], 'html.parser')
                imgs = img_soup.select('img')
                list_gambar = []
                for i in imgs:
                    src = i.get('data-src') or i.get('src')
                    if src and "http" in src:
                        list_gambar.append(src.strip())
                return list_gambar
        
        return []
    except Exception as e:
        print(f"Gagal ambil gambar: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        # 1. Upload Sampul
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        # 2. Ambil Daftar Chapter dari JSON-LD atau Select List
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []

        # Cari di JSON-LD
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                js_data = json.loads(s.string)
                graph = js_data.get('@graph', [js_data])
                for g in graph:
                    if g.get('@type') == 'ItemList':
                        for item in g.get('itemListElement', []):
                            u = item.get('url')
                            if u and '/chapter' in u:
                                name = u.split('/')[-1].replace('-', ' ').title()
                                ch_list.append({"nama": name, "url": u})
            except: continue

        # Jika gagal, ambil dari dropdown <select name="nPL_list"> (Berdasarkan HTML kamu)
        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "https" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})

        if not ch_list: return None
        if limit_ch: ch_list = ch_list[:limit_ch]

        # 3. Scraping Gambar Tiap Chapter
        final_chapters = []
        for ch in ch_list:
            print(f"Scraping Images for: {ch['nama']}...")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(1)

        if not final_chapters: return None
        final_chapters.reverse() # Chapter lama di Index 0

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"BERHASIL: {slug}.json dengan {len(final_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Error fatal {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Mencari katalog terbaru...")
        list_json = []
        # Ambil 2 halaman awal
        for page in range(1, 3):
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('div.mh-77vh > div, .page-item-detail')
            
            if not items: break
            for item in items[:6]:
                try:
                    link_tag = item.select_one('a.fw-600, h3 a')
                    if not link_tag: continue
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.split('/')[-1]
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src')
                    if thumb and not thumb.startswith('http'): thumb = "https://manhuaplus.org" + thumb
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=3)
                    if hasil: list_json.append(hasil)
                except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
