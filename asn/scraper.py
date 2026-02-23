import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import cloudinary
import cloudinary.uploader

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

BASE_URL = "https://rizzcomic.com/manga/?order=update&page=1"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def get_chapter_images(url):
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        imgs = soup.select('#readerarea img')
        return [i.get('src') or i.get('data-src') for i in imgs if i]
    except: return []

def ambil_data():
    if not os.path.exists('db'): os.makedirs('db')
    daftar_utama = []
    
    res = requests.get(BASE_URL, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('.listupd .bs, .listupd .utao')[:10] # Ambil 10 komik terbaru

    for item in items:
        try:
            judul = item.select_one('h3, .tt').text.strip()
            slug = slugify(judul)
            link_detail = item.select_one('a')['href']
            thumb_asli = item.select_one('img').get('data-src') or item.select_one('img').get('src')
            
            # Upload Thumb ke Cloudinary
            thumb_cloud = cloudinary.uploader.upload(thumb_asli, public_id=slug, folder="comic_thumbs")['secure_url']
            
            # Ambil Daftar Chapter (Limit 10)
            res_d = requests.get(link_detail, headers=headers)
            soup_d = BeautifulSoup(res_d.text, 'html.parser')
            ch_list = []
            for ch in soup_d.select('#chapterlist ul li')[:10]:
                ch_list.append({
                    "nama": ch.select_one('.chapternum').text.strip(),
                    "url": ch.select_one('a')['href']
                })

            # Simpan File Detail Individu
            with open(f'db/{slug}.json', 'w', encoding='utf-8') as f:
                json.dump({"judul": judul, "thumb": thumb_cloud, "chapters": ch_list}, f, indent=4)

            daftar_utama.append({
                "judul": judul,
                "slug": slug,
                "thumb": thumb_cloud,
                "genres": [g.text.strip() for g in item.select('.gnre a, .genres a')]
            })
            print(f"Berhasil: {judul}")
            time.sleep(1)
        except Exception as e:
            print(f"Gagal: {e}")

    with open('list.json', 'w', encoding='utf-8') as f:
        json.dump(daftar_utama, f, indent=4)

if __name__ == "__main__":
    ambil_data()
