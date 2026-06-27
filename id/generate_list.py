import os
import json
import datetime

DB_DIR = 'id/db'
OUTPUT_FILE = 'id/list.json'

def generate_list():
    if not os.path.exists(DB_DIR):
        print(f"Folder {DB_DIR} tidak ditemukan")
        return

    comics = []

    for root, dirs, files in os.walk(DB_DIR):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Gagal membaca {filepath}: {e}")
                continue

            slug = filename[:-5]
            judul = data.get('judul', slug)
            thumb = data.get('thumb', '')
            tipe = data.get('tipe', '')
            status = data.get('status', '')
            genre = data.get('genre', [])
            pembaca_total = data.get('pembaca_total', 0)
            chapterCount = data.get('chapterCount', 0)
            last_scraped = data.get('last_scraped')

            if not last_scraped:
                mtime = os.path.getmtime(filepath)
                last_scraped = datetime.datetime.fromtimestamp(mtime).isoformat()

            # Field tambahan untuk detail (bisa juga ditampilkan di index)
            judul_alternatif = data.get('judul_alternatif', '')
            author = data.get('author', '')
            sinopsis = data.get('sinopsis', '')[:150]  # potong untuk ringkasan
            rating = data.get('rating', '')

            comics.append({
                "judul": judul,
                "slug": slug,
                "thumb": thumb,
                "tipe": tipe,
                "status": status,
                "genre": genre,
                "pembaca_total": pembaca_total,
                "chapterCount": chapterCount,
                "last_scraped": last_scraped,
                "judul_alternatif": judul_alternatif,
                "author": author,
                "sinopsis_ringkas": sinopsis,
                "rating": rating
            })

    # Urutkan berdasarkan last_scraped terbaru
    comics.sort(key=lambda x: x['last_scraped'], reverse=True)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(comics, f, indent=2, ensure_ascii=False)

    print(f"✅ list.json diperbarui dengan {len(comics)} komik.")

if __name__ == "__main__":
    generate_list()
