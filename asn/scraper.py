import requests
from bs4 import BeautifulSoup
import json
import time

# Gunakan halaman daftar seri/manga
BASE_URL = "https://rizzcomic.com/manga/?order=update&page=2" 
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def ambil_semua_data():
    semua_komik = []
    halaman_sekarang = 1
    
    # Ganti angka 5 dengan jumlah halaman yang ingin kamu ambil (misal 10 atau 20)
    # Jangan terlalu banyak sekaligus agar tidak diblokir
    max_halaman = 5 

    while halaman_sekarang <= max_halaman:
        url = f"{BASE_URL}{halaman_sekarang}"
        print(f"Memproses Halaman {halaman_sekarang}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200: break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('.utao, .bs, .listupd .bs-item') # Selector tetap sama
            
            if not items: break # Berhenti jika tidak ada komik lagi

            for item in items:
                try:
                    judul = item.select_one('h3, .tt').text.strip()
                    link = item.select_one('a')['href']
                    img_tag = item.select_one('img')
                    img_url = img_tag.get('data-src') or img_tag.get('src')

                    semua_komik.append({
                        "judul": judul,
                        "link": link,
                        "gambar": img_url
                    })
                except:
                    continue
            
            halaman_sekarang += 1
            time.sleep(20) # Jeda 20 detik agar tidak disangka serangan DDOS
            
        except Exception as e:
            print(f"Error di halaman {halaman_sekarang}: {e}")
            break

    # Simpan SEMUA data
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(semua_komik, f, indent=4, ensure_ascii=False)
    
    print(f"Total {len(semua_komik)} komik berhasil diambil!")

if __name__ == "__main__":
    ambil_semua_data()
