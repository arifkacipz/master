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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
TARGET_SLUG = os.environ.get('TARGET_SLUG') # Ambil input dari GitHub

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_images(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        imgs = soup.select('#readerarea img')
        return [i.get('src') or i.get('data-src') or i.get('data-lazy-src') for i in imgs if i]
    except: return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    """Fungsi inti untuk mengambil data chapter sebuah komik"""
    print(f"Sedang memproses: {judul}")
    try:
        # 1. Upload/Get Cloudinary Thumb
        thumb_cloud = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="comic_thumbs")['secure_url']
        
        # 2. Get Chapter List
        res = requests.get(link, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        raw_ch = soup.select('#chapterlist ul li')
        
        # Jika limit_ch ada, hanya ambil bbrp chapter (untuk update rutin)
        if limit_ch: raw_ch = raw_ch[:limit_ch]
        
        ch_data = []
        for c in raw_ch:
            ch_url = c.select_one('a')['href']
            ch_nama = c.select_one('.chapternum').text.strip()
            print(f"  -> Scraping {ch_nama}")
            ch_data.append({
                "nama": ch_nama,
                "images": get_images(ch_url)
            })
            time.sleep(0.5)

        # 3. Simpan ke File Fragmentasi
        if not os.path.exists('db'): os.makedirs('db')
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Error {judul}: {e}")
        return None

def main():
    if TARGET_SLUG:
        # MODE KHUSUS: Scrape Satu Komik Sampai Tuntas
        url = f"https://rizzcomic.com/manga/{TARGET_SLUG}/"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        # MODE NORMAL: Update Katalog 10 Komik Terbaru
        res = requests.get("https://rizzcomic.com/manga/?order=update", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.listupd .bs, .listupd .utao')[:10]
        
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
