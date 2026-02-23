import requests
from bs4 import BeautifulSoup
import json
import time

# URL sumber yang sudah diperbarui
BASE_URL = "https://rizzcomic.com/manga/?order=update&page=" 
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def ambil_data():
    semua_komik = []
    # Kita ambil 3 halaman pertama saja agar aman dari banned IP
    for hal in range(1, 4):
        url = f"{BASE_URL}{hal}"
        print(f"Memproses Halaman {hal}...")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Selector item komik di RizzComic biasanya '.bs' atau '.utao'
            items = soup.select('.listupd .bs, .listupd .utao')
            
            for item in items:
                try:
                    judul = item.select_one('h3, .tt').text.strip()
                    link = item.select_one('a')['href']
                    img_tag = item.select_one('img')
                    img_url = img_tag.get('data-src') or img_tag.get('src')
                    
                    # Mengambil Genre
                    genre_tags = item.select('.gnre a, .genres a')
                    genres = [g.text.strip() for g in genre_tags] if genre_tags else ["Lainnya"]
                    
                    # Mengambil Chapter
                    chap = item.select_one('.epxs, .epzs').text.strip() if item.select_one('.epxs, .epzs') else "Update"

                    semua_komik.append({
                        "judul": judul,
                        "link": link,
                        "gambar": img_url,
                        "chapter_terbaru": chap,
                        "genres": genres
                    })
                except:
                    continue
            time.sleep(20) # Jeda agar tidak dianggap spam
        except Exception as e:
            print(f"Error: {e}")
            break

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(semua_komik, f, indent=4, ensure_ascii=False)
    print(f"Selesai! {len(semua_komik)} komik berhasil disimpan.")

if __name__ == "__main__":
    ambil_data()
