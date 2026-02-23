import requests
from bs4 import BeautifulSoup
import json

# URL Target
TARGET_URL = "https://rizzcomic.com/"

# Header lebih lengkap agar terlihat seperti manusia (User-Agent terbaru)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def ambil_data():
    print(f"Sedang memindai: {TARGET_URL}")
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"Gagal akses web: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    daftar_komik = []

    # Kita coba cari elemen komik dengan beberapa kemungkinan selector (RizzComic sering update)
    items = soup.select('.utao, .bs, .listupd .bs-item, .listupd .utao')
    
    print(f"Ditemukan {len(items)} kotak komik. Mulai memproses...")

    for item in items:
        try:
            # 1. Cari Judul
            judul_tag = item.select_one('h3, h4, .tt, .title')
            if not judul_tag: continue
            judul = judul_tag.text.strip()

            # 2. Cari Link
            link = item.select_one('a')['href']

            # 3. Cari Gambar (Thumbnail)
            img_tag = item.select_one('img')
            # Cek berbagai atribut gambar karena sering pakai 'lazy load'
            img_url = (img_tag.get('data-src') or 
                       img_tag.get('src') or 
                       img_tag.get('data-lazy-src'))

            # 4. Cari Chapter
            chap_tag = item.select_one('.epxs, .epzs, .chapter')
            chapter = chap_tag.text.strip() if chap_tag else "Update"

            daftar_komik.append({
                "judul": judul,
                "link": link,
                "gambar": img_url,
                "chapter_terbaru": chapter
            })
        except:
            continue

    # Simpan hasil
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(daftar_komik, f, indent=4, ensure_ascii=False)
    
    if not daftar_komik:
        print("Peringatan: Data masih kosong. Mungkin selector HTML perlu disesuaikan lagi.")
    else:
        print(f"Sukses! {len(daftar_komik)} komik disimpan ke data.json")

if __name__ == "__main__":
    ambil_data()
