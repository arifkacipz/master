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

# Gunakan Session agar cookie tetap terjaga seperti browser asli
session = requests.Session()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Referer': 'https://manhuaplus.org/',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    try:
        # 1. Dapatkan Chapter ID dari URL (angka di ujung)
        parts = chapter_url.strip('/').split('/')
        chapter_id = parts[-1]
        
        if not chapter_id.isdigit():
            # Jika tidak ada angka di URL, cari di HTML
            res = session.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match:
                chapter_id = match.group(1)
            else:
                return []

        # 2. Ambil gambar via AJAX POST
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = session.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                
                # JALUR 1: Scan semua link cdn.manhuaplus.cc (Cara paling ampuh)
                found_cdn = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
                
                # JALUR 2: Ambil via BeautifulSoup (Jika CDN domain berbeda)
                img_soup = BeautifulSoup(html_content, 'html.parser')
                list_raw = []
                for i in img_soup.find_all('img'):
                    src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
                    if src: list_raw.append(src.strip())
                
                # Gabungkan dan filter
                combined = found_cdn + list_raw
                final_images = []
                seen = set()
                for img in combined:
                    # Normalisasi link
                    if img.startswith('//'): img = "https:" + img
                    elif img.startswith('/'): img = "https://manhuaplus.org" + img
                    
                    # Filter sampah
                    if "loading.gif" in img.lower() or "logo" in img.lower(): continue
                    if img not in seen:
                        final_images.append(img)
                        seen.add(img)
                
                return final_images
        return []
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic Memproses: {judul} ---")
    try:
        # Upload Sampul
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        res = session.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []

        # Ambil daftar chapter dari JSON-LD
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

        # Backup: Ambil dari Select Dropdown
        if not ch_list:
            opts = soup.select('select[name="nPL_list"] option')
            for o in opts:
                val = o.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": o.text.strip(), "url": val})

        if not ch_list: return None
        if limit_ch: ch_list = ch_list[:limit_ch]

        final_chapters = []
        for ch in ch_list:
            print(f"-> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(1.5) # Jeda lebih lama agar tidak diblokir

        if not final_chapters: return None
        final_chapters.reverse()

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"SUKSES: {slug}.json tersimpan.")
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
        print("Scraping katalog utama...")
        list_json = []
        for page in range(1, 3):
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            res = session.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('div.mh-77vh > div, .page-item-detail, .listupd .bs')
            
            if not items: break
            for item in items[:6]:
                try:
                    link_tag = item.select_one('a.fw-600, .post-title a, h3 a')
                    if not link_tag: continue
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.split('/')[-1] if not link.endswith('/') else link.split('/')[-2]
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
