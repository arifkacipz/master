import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

# Config Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

session = requests.Session()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    try:
        # 1. Ekstrak ID langsung dari URL (pola: .../chapter-xxx/92893)
        parts = chapter_url.strip('/').split('/')
        chapter_id = parts[-1]
        
        if not chapter_id.isdigit():
            # Jika tidak ada di URL, bongkar HTML
            res = session.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            chapter_id = match.group(1) if match else None

        if not chapter_id:
            print(f"DEBUG: CHAPTER_ID gagal ditemukan di {chapter_url}")
            return []

        # 2. Ambil gambar via AJAX
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = session.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                img_soup = BeautifulSoup(data['html'], 'html.parser')
                
                # Mengambil link cdn.manhuaplus.cc dan mensortirnya
                temp_list = []
                for i in img_soup.find_all('img'):
                    src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
                    if src and "cdn.manhuaplus.cc" in src and "loading.gif" not in src:
                        if src.startswith('//'): src = "https:" + src
                        temp_list.append(src.strip())
                
                temp_list.sort() # Urutkan berdasarkan timestamp file
                return list(dict.fromkeys(temp_list)) # Hapus duplikat
        return []
    except Exception as e:
        print(f"Error get_images: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        # Upload Sampul
        thumb_cloud = thumb_url
        try:
            if thumb_url and "http" in thumb_url:
                up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
                thumb_cloud = up['secure_url']
        except: pass
        
        res = session.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cari daftar chapter
        ch_list = []
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
            # Dropdown fallback
            opts = soup.select('select[name="nPL_list"] option')
            for o in opts:
                val = o.get('value')
                if val and "https" in val:
                    ch_list.append({"nama": o.text.strip(), "url": val})

        if not ch_list: return None
        if limit_ch: ch_list = ch_list[:limit_ch]

        final_chapters = []
        for ch in ch_list:
            print(f"-> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(1)

        if not final_chapters: return None
        final_chapters.reverse()

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except: return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Mencari katalog terbaru PetoMic...")
        list_json = []
        for page in range(1, 3):
            # Pola URL baru agar lebih stabil
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update"
            print(f"Membuka: {url_katalog}")
            
            res = session.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selektor Katalog Universal (Mencari semua div yang berisi link manga)
            items = soup.select('div.grid > div, div.mh-77vh > div, .page-item-detail, .listupd .bs')
            
            if not items:
                # Fallback jika struktur berubah
                items = soup.find_all('div', class_=re.compile(r'item|detail|post'))

            found_in_page = 0
            for item in items:
                try:
                    a_tag = item.find('a', href=re.compile(r'/manga/'))
                    if not a_tag or not a_tag.get('href'): continue
                    
                    link = a_tag['href']
                    judul = a_tag.get('title') or a_tag.text.strip()
                    if not judul or len(judul) < 2: continue
                    
                    slug = link.strip('/').split('/')[-1]
                    img_tag = item.find('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=2)
                    if hasil:
                        list_json.append(hasil)
                        found_in_page += 1
                except: continue
                if found_in_page >= 8: break # Limit per halaman agar cepat
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"SELESAI: {len(list_json)} komik diproses.")

if __name__ == "__main__":
    main()
