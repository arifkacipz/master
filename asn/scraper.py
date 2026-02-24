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
        # Ambil ID dari URL (Contoh: /92893)
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = session.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            chapter_id = match.group(1) if match else None

        if not chapter_id: return []

        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = session.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                img_soup = BeautifulSoup(data['html'], 'html.parser')
                temp_list = []
                for i in img_soup.find_all('img'):
                    src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
                    if src and "cdn.manhuaplus.cc" in src and "loading.gif" not in src:
                        if src.startswith('//'): src = "https:" + src
                        temp_list.append(src.strip())
                
                temp_list.sort() # Urutkan agar tidak acak
                return list(dict.fromkeys(temp_list))
        return []
    except: return []

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
        
        # Ambil daftar chapter (JSON-LD)
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
            # Dropdown Fallback
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
            time.sleep(0.5)

        if not final_chapters: return None
        final_chapters.reverse()

        # Pastikan path absolut ke folder db di dalam asn/
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'db')
        os.makedirs(db_path, exist_ok=True)
        
        file_path = os.path.join(db_path, f"{slug}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"BERHASIL: {file_path} tercipta.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Gagal: {e}")
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
            # URL Sesuai permintaan Anda
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            
            print(f"Membuka: {url_katalog}")
            res = session.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selector Super Fleksibel: Cari semua <a> yang punya link /manga/
            items = soup.find_all('a', href=re.compile(r'/manga/'))
            
            processed_slugs = set()
            found_in_page = 0
            for a in items:
                try:
                    link = a['href']
                    slug = link.strip('/').split('/')[-1]
                    if slug in processed_slugs or "all-manga" in slug: continue
                    
                    judul = a.get('title') or a.text.strip()
                    if not judul or len(judul) < 3: continue
                    
                    # Cari gambar di sekitar elemen <a> tersebut
                    parent = a.find_parent('div')
                    img_tag = parent.find('img') if parent else None
                    thumb = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=2)
                    if hasil:
                        list_json.append(hasil)
                        processed_slugs.add(slug)
                        found_in_page += 1
                except: continue
                if found_in_page >= 8: break
        
        # Simpan list.json di folder yang sama dengan script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, 'list.json'), 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"SELESAI: {len(list_json)} komik masuk katalog.")

if __name__ == "__main__":
    main()
