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
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Referer': 'https://asuracomic.net/'
}
TARGET_SLUG = os.environ.get('TARGET_SLUG')

def get_images_from_chapter(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Radar diperkuat untuk mencari di semua kemungkinan tag gambar pembaca
        imgs = soup.select('#readerarea img, .rdminimal img, .entry-content img, .main-reading-area img, .img-responsive')
        list_gambar = []
        for i in imgs:
            # Mencari di berbagai atribut (Lazy Load Protection)
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src') or i.get('data-srcset')
            if src and "http" in src:
                # Abaikan gambar sampah (logo, discord, dsb)
                if any(x in src.lower() for x in ["logo", "banner", "discord", "donation", "loading"]): continue
                list_gambar.append(src.strip())
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
        
        # Selector Daftar Chapter diperkuat
        raw_ch = soup.select('#chapterlist ul li, .cl-list ul li, .eplister ul li')
        
        if not raw_ch:
            print(f"DEBUG: Tidak ada chapter ditemukan untuk {judul}")
            return None

        if limit_ch: raw_ch = raw_ch[:limit_ch]
        
        ch_data = []
        for c in raw_ch:
            a_tag = c.select_one('a')
            if not a_tag: continue
            ch_url = a_tag['href']
            ch_nama = c.select_one('.chapternum, .chapter-name, span, .cl-name').text.strip()
            
            print(f"Scraping: {ch_nama}...")
            images = get_images_from_chapter(ch_url)
            if images:
                ch_data.append({"nama": ch_nama, "images": images})
            time.sleep(1)

        if not ch_data: return None
        
        ch_data.reverse() # Index 0 = Chapter Paling Lama

        # Memastikan folder db benar-benar ada sebelum menulis file
        os.makedirs('db', exist_ok=True)
        with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_data}, f, indent=4)
        
        print(f"BERHASIL: db/{slug}.json tercipta dengan {len(ch_data)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"ERROR: {judul} gagal - {e}")
        return None

def main():
    if TARGET_SLUG:
        url = f"https://asuracomic.net/series/{TARGET_SLUG}/"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Menarik katalog terbaru PetoMic...")
        res = requests.get("https://asuracomic.net/series?page=1", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Radar Katalog diperkuat (Asura sering pakai .uta atau .bsx)
        items = soup.select('.listupd .bs, .utao .uta, .listupd .bsx, .soralist ul li, .grid-item')[:12]
        
        if not items:
            print("GAGAL: Radar tidak menemukan komik di halaman utama. Mencoba selector alternatif...")
            # Percobaan kedua dengan selector lebih umum
            items = soup.find_all('div', class_='bs') or soup.find_all('div', class_='uta')
        
        if not items:
            print("GAGAL TOTAL: Website sumber mungkin sedang memblokir robot.")
            return

        list_json = []
        for item in items:
            try:
                judul_tag = item.select_one('h4, .tt, h3, .bigor .tt, .series, .title')
                link_tag = item.select_one('a')
                if not judul_tag or not link_tag: continue
                
                judul = judul_tag.text.strip()
                link = link_tag['href']
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
