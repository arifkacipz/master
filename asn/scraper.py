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
        # 1. Ambil ID dari URL
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        # 2. Request ke AJAX Server
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                img_soup = BeautifulSoup(data['html'], 'html.parser')
                imgs = img_soup.select('img')
                
                list_gambar = []
                for i in imgs:
                    # PRIORITAS: Ambil data-src, lalu src jika data-src tidak ada
                    # FILTER: Abaikan jika ada kata 'loading.gif'
                    src = i.get('data-src') or i.get('src')
                    
                    if src and "loading.gif" not in src:
                        if src.startswith('//'):
                            src = "https:" + src
                        elif src.startswith('/'):
                            src = "https://manhuaplus.org" + src
                        list_gambar.append(src.strip())
                return list_gambar
        return []
    except Exception as e:
        print(f"DEBUG: Gagal ambil gambar di {chapter_url}: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []

        # Ambil dari JSON-LD
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
            except: continue

        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})

        if not ch_list: return None
        if limit_ch: ch_list = ch_list[:limit_ch]

        final_chapters = []
        for ch in ch_list:
            print(f"-> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(1) # Jeda agar tidak dianggap serangan bot

        if not final_chapters: return None
        final_chapters.reverse()

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"BERHASIL: {slug}.json tersimpan.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Error {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Menarik katalog terbaru...")
        list_json = []
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
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=2)
                    if hasil: list_json.append(hasil)
                except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
