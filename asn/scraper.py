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

session = requests.Session()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/all-manga/',
    'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = session.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = session.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                img_soup = BeautifulSoup(data['html'], 'html.parser')
                temp_list = []
                for i in img_soup.find_all('img'):
                    src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
                    if src:
                        src = src.strip()
                        if src.startswith('//'): src = "https:" + src
                        elif src.startswith('/'): src = "https://manhuaplus.org" + src
                        if "cdn.manhuaplus.cc" in src and "loading.gif" not in src:
                            temp_list.append(src)
                
                temp_list.sort()
                final_images = []
                for img in temp_list:
                    if img not in final_images: final_images.append(img)
                return final_images
        return []
    except: return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic Memproses: {judul} ---")
    try:
        # Upload Sampul (Opsional jika API Cloudinary salah/limit)
        thumb_cloud = thumb_url
        try:
            if thumb_url and "http" in thumb_url:
                up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
                thumb_cloud = up['secure_url']
        except: pass
        
        res = session.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []

        # JSON-LD Extractor
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
            print(f"Peringatan: Tidak ada chapter untuk {judul}. Dilewati.")
            return None

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
    except Exception as e:
        print(f"Error proses {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Mencari katalog terbaru PetoMic...")
        list_json = []
        for page in range(1, 3):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            
            print(f"Membuka: {url_katalog}")
            res = session.get(url_katalog, headers=HEADERS)
            
            # CEK STATUS: Jika 403, berarti terblokir Cloudflare
            if res.status_code != 200:
                print(f"GAGAL: Website memberikan status {res.status_code}. Robot mungkin terblokir.")
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selector Katalog yang diperluas agar tidak luput
            items = soup.select('div[class*="mh-77vh"] > div, .page-item-detail, .listupd .bs, .grid > div')
            
            if not items:
                print(f"DEBUG: Halaman {page} tidak menemukan item komik. Mencoba selector alternatif...")
                items = soup.find_all('div', class_='text-center') # Selector cadangan paling dasar

            found_count = 0
            for item in items:
                try:
                    # Mencari link judul di dalam tag <a> yang memiliki class fw-600 atau di dalam <h3>
                    link_tag = item.select_one('a.fw-600, .post-title a, h3 a, a[title]')
                    if not link_tag: continue
                    
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    
                    # Validasi URL
                    if "manga" not in link: continue

                    slug = link.strip('/').split('/')[-1]
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src')
                    if thumb and not thumb.startswith('http'): thumb = "https://manhuaplus.org" + thumb
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=2)
                    if hasil: 
                        list_json.append(hasil)
                        found_count += 1
                except: continue
                if found_count >= 6: break # Batasi agar tidak overload per halaman
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"SELESAI: Menghasilkan {len(list_json)} komik ke list.json")

if __name__ == "__main__":
    main()
