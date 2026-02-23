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

def get_images_from_chapter(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        # ManhuaPlus biasanya menyimpan gambar di dalam div reading-content
        imgs = soup.select('.reading-content img, #readerarea img, .page-break img')
        list_gambar = []
        for i in imgs:
            # Mengambil URL dari berbagai atribut (Lazy Load)
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src')
            if src and "http" in src:
                # Filter gambar non-komik (iklan/logo)
                if any(x in src.lower() for x in ["logo", "banner", "discord", "donation", "loading"]): continue
                list_gambar.append(src.strip())
        return list_gambar
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    try:
        # 1. Upload Sampul ke Cloudinary
        thumb_cloud = ""
        if thumb_url and "http" in thumb_url:
            print(f"Mengunggah sampul PetoMic: {slug}...")
            up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
            thumb_cloud = up['secure_url']
        
        # 2. Ambil Daftar Chapter
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selector khusus ManhuaPlus untuk daftar chapter
        raw_ch = soup.select('.wp-manga-chapter, li.wp-manga-chapter, #chapterlist ul li')
        
        if not raw_ch:
            print(f"DEBUG: Gagal menemukan daftar chapter untuk {judul}")
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
        
        # LOGIKA: INDEX 0 = CHAPTER PALING LAMA (Awal)
        ch_data.reverse()

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
        # Berdasarkan metadata kamu: pola URL-nya adalah /manga/slug
        url = f"https://manhuaplus.org/manga/{TARGET_SLUG}"
        process_comic(TARGET_SLUG.replace('-', ' ').title(), url, TARGET_SLUG, "", limit_ch=None)
    else:
        print("Menarik katalog terbaru ManhuaPlus ke PetoMic...")
        res = requests.get("https://manhuaplus.org/all-manga/page/1/", headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selector untuk item komik di ManhuaPlus
        items = soup.select('.page-item-detail, .listupd .bs, .manga-item')[:12]
        
        if not items:
            print("GAGAL: Tidak menemukan daftar komik. Selector utama tidak cocok.")
            return

        list_json = []
        for item in items:
            try:
                judul_tag = item.select_one('h4, .tt, h3, .post-title h3')
                link_tag = item.select_one('a')
                if not judul_tag or not link_tag: continue
                
                judul = judul_tag.text.strip()
                link = link_tag['href']
                # Mengambil slug dari URL link
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
