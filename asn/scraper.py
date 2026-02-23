import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import cloudinary
import cloudinary.uploader

# Konfigurasi Cloudinary (Ambil dari GitHub Secrets)
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

BASE_URL = "https://rizzcomic.com/manga/?order=update&page=1"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_images_from_chapter(url):
    """Mengambil semua link gambar di dalam satu halaman chapter"""
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selector umum untuk area baca di situs WordPress Manga
        imgs = soup.select('#readerarea img')
        return [i.get('src') or i.get('data-src') or i.get('data-lazy-src') for i in imgs if i]
    except:
        return []

def ambil_data():
    if not os.path.exists('db'): os.makedirs('db')
    daftar_utama = []
    
    print("Memulai Deep Scraping...")
    res = requests.get(BASE_URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('.listupd .bs, .listupd .utao')[:8] # Ambil 8 komik terbaru agar tidak timeout

    for item in items:
        try:
            judul = item.select_one('h3, .tt').text.strip()
            slug = slugify(judul)
            link_detail = item.select_one('a')['href']
            thumb_asli = item.select_one('img').get('data-src') or item.select_one('img').get('src')
            
            # 1. Upload Sampul ke Cloudinary
            thumb_cloud = cloudinary.uploader.upload(thumb_asli, public_id=slug, folder="comic_thumbs")['secure_url']
            
            # 2. Masuk ke halaman detail untuk daftar chapter
            res_d = requests.get(link_detail, headers=headers)
            soup_d = BeautifulSoup(res_d.text, 'html.parser')
            ch_list = []
            
            # Ambil 5 chapter terbaru saja agar robot cepat dan file tidak bengkak
            raw_chapters = soup_d.select('#chapterlist ul li')[:5]
            for ch in raw_chapters:
                ch_url = ch.select_one('a')['href']
                ch_nama = ch.select_one('.chapternum').text.strip()
                
                print(f"  > Mengambil gambar: {judul} - {ch_nama}")
                images = get_images_from_chapter(ch_url)
                
                ch_list.append({
                    "nama": ch_nama,
                    "images": images
                })
                time.sleep(0.5)

            # 3. Simpan File Fragmentasi
            with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
                json.dump({"judul": judul, "chapters": ch_list}, f, indent=4)

            daftar_utama.append({"judul": judul, "slug": slug, "thumb": thumb_cloud})
            time.sleep(1)
        except Exception as e:
            print(f"Gagal memproses {judul}: {e}")

    with open('list.json', 'w', encoding='utf-8') as f:
        json.dump(daftar_utama, f, indent=4)

if __name__ == "__main__":
    ambil_data()
