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
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Referer': 'https://manhuaplus.org/'
}
TARGET_SLUG = os.environ.get('TARGET_SLUG')

def get_images(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Mencari gambar di area pembaca ManhuaPlus
        imgs = soup.select('.reading-content img, #readerarea img, .page-break img')
        list_gambar = []
        for i in imgs:
            src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
            if src and "http" in src:
                if any(x in src.lower() for x in ["logo", "banner", "discord", "donation"]): continue
                list_gambar.append(src.strip())
        return list_gambar
    except: return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        # 1. Upload Sampul
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        # 2. Ambil Chapter
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selector Chapter sesuai script HTML ManhuaPlus (ul#myUL)
        raw_links = soup.select('ul#myUL li.chapter a')
        if not raw_links: raw_links = soup.select('.wp-manga-chapter a')

        if not raw_links: return None
        if limit_ch: raw_links = raw_links[:limit_ch]
        
        ch_data = []
        for a_tag in raw_links:
            ch_url = a_tag['href']
            ch_nama = a_tag.text.strip()
            print(f"Scraping: {ch_nama}...")
            images = get_images(ch_url)
            if images:
                ch_data.append({"nama": ch_nama, "images": images})
            time.sleep(0.5)

        ch_data.reverse() # Index 0 = Chapter Terlama

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    if TARGET_SLUG:
        url = f"https://manhuaplus.org/manga/{TARGET_SLUG}"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Mencari katalog terbaru PetoMic...")
        list_json = []
        # Mengambil 3 halaman awal
        for page in range(1, 4):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                # URL Halaman 2 dan seterusnya sesuai permintaan terbaru kamu
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            
            print(f"Membuka halaman: {url_katalog}")
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selector grid berdasarkan skrip HTML yang kamu kirim (div.mh-77vh > div)
            items = soup.select('div.mh-77vh > div')
            
            if not items: 
                print(f"DEBUG: Tidak ditemukan item di halaman {page}")
                break

            for item in items[:8]: # Ambil 8 per halaman agar cepat
                try:
                    # Mencari link judul di .text-center a.fw-600 sesuai skrip HTML kamu
                    link_tag = item.select_one('.text-center a.fw-600')
                    if not link_tag: continue
                    
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                    
                    # Mencari Sampul di data-src (lazy load)
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src')
                    if thumb and not thumb.startswith('http'): 
                        thumb = "https://manhuaplus.org" + thumb
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=3)
                    if hasil: list_json.append(hasil)
                except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
