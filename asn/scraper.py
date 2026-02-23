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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/'
}
TARGET_SLUG = os.environ.get('TARGET_SLUG')

def get_images_from_chapter(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        # ManhuaPlus menggunakan .reading-content img
        imgs = soup.select('.reading-content img, .page-break img, #readerarea img')
        list_gambar = []
        for i in imgs:
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src')
            if src and "http" in src:
                if any(x in src.lower() for x in ["logo", "banner", "discord", "donation", "loading"]): continue
                list_gambar.append(src.strip())
        return list_gambar
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"PetoMic memproses: {judul}")
    try:
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            print(f"Mengunggah sampul: {slug}...")
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selector ManhuaPlus: .wp-manga-chapter
        raw_ch = soup.select('.wp-manga-chapter')
        if not raw_ch:
            raw_ch = soup.select('#chapterlist ul li')

        if not raw_ch:
            print(f"DEBUG: Chapter tidak ditemukan untuk {judul}")
            return None

        if limit_ch: raw_ch = raw_ch[:limit_ch]
        
        ch_data = []
        for c in raw_ch:
            a_tag = c.select_one('a')
            if not a_tag: continue
            ch_url = a_tag['href']
            ch_nama = a_tag.text.strip()
            
            print(f"Scraping: {ch_nama}...")
            images = get_images_from_chapter(ch_url)
            if images:
                ch_data.append({"nama": ch_nama, "images": images})
            time.sleep(1.2)

        if not ch_data: return None
        ch_data.reverse() # Index 0 = Paling Lama

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
        url = f"https://manhuaplus.org/manga/{TARGET_SLUG}/"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Menarik katalog terbaru PetoMic dari ManhuaPlus...")
        res = requests.get("https://manhuaplus.org/all-manga/page/1/", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Radar Katalog: ManhuaPlus sering pakai .page-item-detail
        items = soup.select('.page-item-detail, .listupd .bs, .manga')[:10]
        
        if not items:
            print("GAGAL: Radar tidak menemukan komik. Mencoba selector alternatif...")
            items = soup.find_all('div', class_='page-item-detail') or soup.find_all('div', class_='bs')
        
        if not items:
            print("GAGAL TOTAL: Website sumber mungkin sedang memblokir atau struktur berubah.")
            return

        list_json = []
        for item in items:
            try:
                judul_tag = item.select_one('.post-title h3 a, h4 a, .tt a, h3 a')
                if not judul_tag: continue
                
                judul = judul_tag.text.strip()
                link = judul_tag['href']
                slug = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
                
                img_tag = item.select_one('img')
                thumb = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-lazy-src')
                
                hasil = process_comic(judul, link, slug, thumb, limit_ch=3)
                if hasil: list_json.append(hasil)
            except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
