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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Referer': 'https://manhuaplus.org/'
}
TARGET_SLUG = os.environ.get('TARGET_SLUG')

def get_images_from_chapter(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selector ManhuaPlus berdasarkan HTML yang kamu berikan
        imgs = soup.select('.reading-content img, #readerarea img, .page-break img')
        list_gambar = []
        for i in imgs:
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src') or i.get('data-srcset')
            if src and "http" in src:
                if any(x in src.lower() for x in ["logo", "banner", "discord", "donation", "loading"]): continue
                list_gambar.append(src.strip())
        
        if not list_gambar:
            found = re.findall(r'(https?://[^\s"\']+\.(?:jpg|jpeg|png|webp))', res.text)
            if found: list_gambar.extend([f for f in found if "manhuaplus" not in f.lower() or "uploads/covers" not in f.lower()])
            
        return list_gambar
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            print(f"Mengunggah sampul: {slug}...")
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selector Daftar Chapter ManhuaPlus (ul#myUL li.chapter a)
        raw_links = soup.select('ul#myUL li.chapter a')
        if not raw_links:
            raw_links = soup.select('.wp-manga-chapter a') 

        if not raw_links:
            print(f"DEBUG: Chapter tidak ditemukan untuk {judul}")
            return None

        if limit_ch: raw_links = raw_links[:limit_ch]
        
        ch_data = []
        for a_tag in raw_links:
            ch_url = a_tag['href']
            ch_nama = a_tag.text.strip()
            
            print(f"Scraping: {ch_nama}...")
            images = get_images_from_chapter(ch_url)
            if images:
                ch_data.append({"nama": ch_nama, "images": images})
            time.sleep(1.2)

        if not ch_data: return None
        ch_data.reverse() # Index 0 = Chapter Terlama (Awal)

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        print(f"BERHASIL: db/{slug}.json tercipta.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"ERROR: {judul} gagal - {e}")
        return None

def main():
    if TARGET_SLUG:
        url = f"https://manhuaplus.org/manga/{TARGET_SLUG}"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Menarik katalog terbaru PetoMic...")
        list_json = []
        
        # Logika Paginasi (Contoh ambil 2 halaman pertama untuk update rutin)
        for page in range(1, 3):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/page/{page}/"
            
            print(f"Membuka halaman: {url_katalog}")
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            items = soup.select('.page-item-detail, .listupd .bs, .manga-item')
            if not items: break

            for item in items[:8]: # Ambil 8 per halaman agar tidak timeout
                try:
                    judul_tag = item.select_one('.post-title h3 a, h4 a, .tt a')
                    if not judul_tag: continue
                    
                    judul = judul_tag.text.strip()
                    link = judul_tag['href']
                    slug = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                    
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
                    if hasil: list_json.append(hasil)
                except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
