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
        res = requests.get(url, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selector untuk gambar di AsuraComic
        imgs = soup.select('#readerarea img, .rdminimal img')
        list_gambar = []
        for i in imgs:
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src')
            if src and "http" in src and "asuracomic" not in src.lower(): # Menghindari logo asura jika ada
                list_gambar.append(src.strip())
        return list_gambar
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"Sedang memproses: {judul}")
    try:
        # 1. Upload/Get Cloudinary Thumb
        thumb_cloud = ""
        if thumb_url:
            thumb_cloud = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="asura_thumbs")['secure_url']
        
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
            images = get_images_from_chapter(ch_url)
            
            if images:
                ch_data.append({"nama": ch_nama, "images": images})
            time.sleep(0.8)

        # INDEX 0 = CHAPTER PALING LAMA
        ch_data.reverse()

        if not os.path.exists('db'): os.makedirs('db')
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Error {judul}: {e}")
        return None

def main():
    if TARGET_SLUG:
        print(f"--- MODE KHUSUS: Full Scrape Asura {TARGET_SLUG} ---")
        url = f"https://asuracomic.net/series/{TARGET_SLUG}/"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("--- MODE NORMAL: Update Katalog Asura ---")
        # URL Series Asura
        res = requests.get("https://asuracomic.net/series?page=1", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selector Asura: Mencari kotak komik
        items = soup.select('.listupd .bs, .utao .uta')[:10]
        
        list_json = []
        for item in items:
            try:
                judul = item.select_one('h4, .tt, h3').text.strip()
                link = item.select_one('a')['href']
                slug = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                img_tag = item.select_one('img')
                thumb = img_tag.get('src') or img_tag.get('data-src')
                
                hasil = process_comic(judul, link, slug, thumb, limit_ch=3)
                if hasil: list_json.append(hasil)
            except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
