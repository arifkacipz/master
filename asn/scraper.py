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
        # 1. Ekstrak Chapter ID dari URL
        chapter_id = chapter_url.strip('/').split('/')[-1]
        
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        # 2. Ambil data gambar via AJAX POST
        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
        
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                
                # Mengambil link dari cdn.manhuaplus.cc lewat Regex
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
                
                # Saring link (hapus loading.gif dan duplikat)
                temp_list = []
                seen = set()
                for img in list_gambar:
                    img = img.strip()
                    if "loading.gif" not in img and img not in seen:
                        temp_list.append(img)
                        seen.add(img)
                
                # --- FITUR PENTING: URUTKAN BERDASARKAN TIMESTAMP NAMA FILE ---
                # Ini mencegah gambar acak (urutkan secara alfabetis/numeric)
                temp_list.sort()

                return temp_list
        return []
    except Exception as e:
        print(f"Error get_images: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        # Upload Sampul ke Cloudinary
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            try:
                up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
                thumb_cloud = up['secure_url']
            except:
                thumb_cloud = thumb_url # Fallback jika Cloudinary gagal
        
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list = []

        # Jalur 1: Ambil dari JSON-LD
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

        # Jalur 2: Dropdown Menu (Backup)
        if not ch_list:
            options = soup.select('select[name="nPL_list"] option')
            for opt in options:
                val = opt.get('value')
                if val and "manhuaplus.org" in val:
                    ch_list.append({"nama": opt.text.strip(), "url": val})

        if not ch_list: return None
        
        # --- PERUBAHAN: AMBIL 10 CHAPTER TERBARU ---
        if limit_ch: 
            ch_list = ch_list[:limit_ch]

        final_chapters = []
        for ch in ch_list:
            print(f"   -> Scraping Chapter: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(0.8) # Jeda sedikit agar tidak kena blokir

        if not final_chapters: return None
        
        # Urutan baca (Chapter terlama di awal list JSON)
        final_chapters.reverse()

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"SUKSES: {slug}.json tersimpan.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        # Jika target slug manual, ambil semua chapter (limit_ch=None)
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Scraping katalog rutin PetoMic (Halaman 1-3)...")
        list_json = []
        
        for page in range(1, 4):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            
            print(f"\n[!] Membuka halaman: {url_katalog}")
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Mengambil SEMUA item di halaman (menghapus batasan [:8])
            items = soup.select('div.mh-77vh > div, .page-item-detail, .listupd .bs')
            
            if not items: 
                print("Halaman kosong atau selector berubah.")
                break
            
            print(f"Menemukan {len(items)} judul komik. Memulai proses...")

            for item in items:
                try:
                    link_tag = item.select_one('a.fw-600, .post-title a, h3 a')
                    if not link_tag: continue
                    
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.split('/')[-1] if not link.endswith('/') else link.split('/')[-2]
                    
                    # Ambil sampul
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src')
                    if thumb and not thumb.startswith('http'): 
                        thumb = "https://manhuaplus.org" + thumb
                    
                    # --- PERUBAHAN: LIMIT 10 CHAPTER PER KOMIK ---
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=10)
                    if hasil: 
                        list_json.append(hasil)
                except Exception as e:
                    print(f"Skip item karena error: {e}")
                    continue
        
        # Simpan katalog utama
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)
        print(f"\n--- SELESAI: Total {len(list_json)} komik masuk katalog ---")

if __name__ == "__main__":
    main()
