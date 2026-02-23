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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
TARGET_SLUG = os.environ.get('TARGET_SLUG')

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_images_from_chapter(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selector khusus RizzComic dan cadangan
        imgs = soup.select('#readerarea img, .reading-content img, .entry-content img')
        list_gambar = []
        for i in imgs:
            src = i.get('data-src') or i.get('src') or i.get('data-lazy-src')
            if src and "http" in src:
                list_gambar.append(src.strip())
        return list_gambar
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"Sedang memproses: {judul}")
    try:
        # 1. Upload/Get Cloudinary Thumb
        thumb_cloud = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="comic_thumbs")['secure_url']
        
        # 2. Get Chapter List
        res = requests.get(link, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        raw_ch = soup.select('#chapterlist ul li')
        
        if limit_ch: raw_ch = raw_ch[:limit_ch]
        
        ch_data = []
        for c in raw_ch:
            ch_url = c.select_one('a')['href']
            ch_nama = c.select_one('.chapternum').text.strip()
            print(f"  -> Scraping {ch_nama}")
            ch_data.append({
                "nama": ch_nama,
                "images": get_images_from_chapter(ch_url)
            })
            time.sleep(0.5)

        if not os.path.exists('db'): os.makedirs('db')
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    if TARGET_SLUG:
        print(f"--- MODE KHUSUS: Full Scrape {TARGET_SLUG} ---")
        url = f"https://rizzcomic.com/manga/{TARGET_SLUG}/"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("--- MODE NORMAL: Update Katalog ---")
        res = requests.get("https://rizzcomic.com/manga/?order=update", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.listupd .bs, .listupd .utao')[:12]
        
        list_json = []
        for item in items:
            judul = item.select_one('h3, .tt').text.strip()
            link = item.select_one('a')['href']
            slug = slugify(judul)
            thumb = item.select_one('img').get('data-src') or item.select_one('img').get('src')
            
            hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
            if hasil: list_json.append(hasil)
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
