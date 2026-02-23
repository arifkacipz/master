import requests
from bs4 import BeautifulSoup
import json

# URL Target
TARGET_URL = "https://rizzcomic.com/"

# Header agar tidak diblokir (berpura-pura jadi browser Chrome)
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def ambil_data_rizz():
    print("Memulai pengambilan data...")
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        print(f"Gagal akses web. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    daftar_komik = []

    # Mencari kotak daftar update terbaru
    # Di RizzComic, biasanya setiap item berada di dalam class 'utao' atau 'bs'
    items = soup.select('.listupd .utao') 

    for item in items:
        try:
            # Mengambil Judul
            judul = item.select_one('h3').text.strip()
            
            # Mengambil Link Komik
            link = item.select_one('a')['href']
            
            # Mengambil Link Gambar (Thumbnail)
            img_tag = item.select_one('img')
            img_url = img_tag.get('src') or img_tag.get('data-src') # Beberapa web pakai lazy-load

            # Mengambil Chapter Terbaru (Tambahan)
            chapter = item.select_one('.epxs').text.strip() if item.select_one('.epxs') else "N/A"

            daftar_komik.append({
                "judul": judul,
                "link": link,
                "gambar": img_url,
                "chapter_terbaru": chapter
            })
        except Exception as e:
            continue

    # Simpan ke data.json
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(daftar_komik, f, indent=4, ensure_ascii=False)
    
    print(f"Berhasil mengambil {len(daftar_komik)} komik!")

if __name__ == "__main__":
    ambil_data_rizz()
