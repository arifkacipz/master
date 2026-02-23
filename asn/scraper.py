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
        # Selector gambar pembaca
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
        
        ch_data = []
        
        # JALUR 1: Ekstraksi dari JSON-LD (Paling Akurat untuk ManhuaPlus)
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                js_data = json.loads(s.string)
                # Mencari pola ItemList yang berisi daftar chapter
                if js_data.get('@type') == 'ItemList' or '@graph' in js_data:
                    items = js_data.get('itemListElement', [])
                    if not items and '@graph' in js_data:
                        for g in js_data['@graph']:
                            if g.get('@type') == 'ItemList':
                                items = g.get('itemListElement', [])
                                break
                    
                    for item in items:
                        ch_url = item.get('url')
                        # Ambil nama chapter dari URL (misal: chapter-103)
                        ch_nama_raw = ch_url.split('/')[-2] if ch_url.endswith('/') else ch_url.split('/')[-1]
                        ch_nama = ch_nama_raw.replace('-', ' ').title()
                        
                        if ch_url and 'chapters' in ch_url:
                            ch_data.append({"nama": ch_nama, "url": ch_url})
            except: continue

        # JALUR 2: Jika Jalur 1 Gagal, gunakan HTML Selector biasa
        if not ch_data:
            raw_links = soup.select('ul#myUL li.chapter a, .wp-manga-chapter a')
            for a in raw_links:
                ch_data.append({"nama": a.text.strip(), "url": a['href']})

        if not ch_data:
            print(f"Gagal total menemukan chapter untuk {judul}")
            return None

        # Batasi jumlah chapter jika bukan Full Scrape
        if limit_ch: ch_data = ch_data[:limit_ch]
        
        # Scraping gambar di setiap chapter
        final_chapters = []
        for ch in ch_data:
            print(f"Scraping Images: {ch['nama']}...")
            imgs = get_images(ch['url'])
            if imgs:
                final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(1)

        # LOGIKA: INDEX 0 = CHAPTER TERLAMA
        final_chapters.reverse()

        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": final_chapters}, f, indent=4)
        
        print(f"BERHASIL: db/{slug}.json")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Error fatal {judul}: {e}")
        return None

def main():
    if TARGET_SLUG:
        url = f"https://manhuaplus.org/manga/{TARGET_SLUG}"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Mencari katalog terbaru PetoMic...")
        list_json = []
        # Ambil 3 halaman
        for page in range(1, 4):
            if page == 1:
                url_katalog = "https://manhuaplus.org/all-manga/"
            else:
                url_katalog = f"https://manhuaplus.org/all-manga/{page}/?sort=last_update&status=0"
            
            print(f"Membuka: {url_katalog}")
            res = requests.get(url_katalog, headers=HEADERS)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selector Katalog (Sesuai skrip HTML terbaru kamu)
            items = soup.select('div.mh-77vh > div, .page-item-detail, .listupd .bs')
            if not items: break

            for item in items[:8]:
                try:
                    link_tag = item.select_one('a.fw-600, .post-title a, h3 a')
                    if not link_tag: continue
                    
                    judul = link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                    
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
