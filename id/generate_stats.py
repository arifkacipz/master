import os
import json

DB_DIR = 'id/db'
OUTPUT_FILE = 'id/stats.json'

def generate_stats():
    if not os.path.exists(DB_DIR):
        print(f"Folder {DB_DIR} tidak ditemukan")
        return

    low_manga = []

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
            chapterCount = data.get('chapterCount', 0)
            online = data.get('online', 0)
            tipe = data.get('tipe', '')
            status = data.get('status', '')

            # Masukkan jika chapter kurang dari 15
            if chapterCount < 15:
                low_manga.append({
                    "slug": slug,
                    "judul": judul,
                    "thumb": thumb,
                    "chapterCount": chapterCount,
                    "online": online,
                    "tipe": tipe,
                    "status": status
                })

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(low_manga, f, indent=2, ensure_ascii=False)

    print(f"✅ stats.json diperbarui dengan {len(low_manga)} komik (chapterCount < 15).")

if __name__ == "__main__":
    generate_stats()
