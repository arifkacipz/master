import os
import json
import glob
import datetime

def generate_list_from_db():
    """
    Membaca semua file JSON di folder db/ (termasuk subfolder) dan menghasilkan list.json
    yang berisi daftar komik (judul, slug, thumb, Updated) diurutkan berdasarkan
    last_scraped terbaru (descending).
    Field 'Updated' diambil dari field 'last_scraped' di dalam file JSON.
    Jika tidak ada, fallback ke waktu modifikasi file (untuk komik lama).
    """
    comics = []

    # Gunakan os.walk untuk memindai semua subfolder
    for root, dirs, files in os.walk('db'):
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    slug = filename[:-5]
                    judul = data.get('judul', slug)
                    thumb = data.get('thumb', '')

                    # Ambil last_scraped dari data, fallback ke mtime file
                    last_scraped = data.get('last_scraped')
                    if not last_scraped:
                        mtime = os.path.getmtime(filepath)
                        last_scraped = datetime.datetime.fromtimestamp(mtime).isoformat()

                    comics.append({
                        "judul": judul,
                        "slug": slug,
                        "thumb": thumb,
                        "Updated": last_scraped,
                        "_sort": last_scraped  # untuk sorting
                    })
                except Exception as e:
                    print(f"Gagal membaca {filepath}: {e}")

    # Urutkan berdasarkan Updated terbaru (descending)
    comics.sort(key=lambda x: x['_sort'], reverse=True)

    # Hapus field temporary sebelum disimpan
    for comic in comics:
        del comic['_sort']

    # Simpan ke list.json
    with open('list.json', 'w', encoding='utf-8') as f:
        json.dump(comics, f, indent=4)

    print(f"✅ Berhasil membuat list.json dengan {len(comics)} komik (diurutkan update terbaru).")

if __name__ == "__main__":
    generate_list_from_db()
