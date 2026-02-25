import os
import json
import glob

def generate_list_from_db2():
    """
    Membaca semua file JSON di folder db2/ dan menghasilkan list.json
    yang berisi daftar komik (judul, slug, thumb) diurutkan berdasarkan
    waktu modifikasi file terbaru (descending).
    """
    # Cari semua file JSON di folder db
    json_files = glob.glob('db2/*.json')
    comics = []

    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ambil slug dari nama file (tanpa ekstensi)
            slug = os.path.splitext(os.path.basename(filepath))[0]
            judul = data.get('judul', slug)  # fallback ke slug jika judul tidak ada
            thumb = data.get('thumb', '')

            # Dapatkan waktu modifikasi file (timestamp)
            mtime = os.path.getmtime(filepath)

            comics.append({
                "judul": judul,
                "slug": slug,
                "thumb": thumb,
                "mtime": mtime  # sementara untuk sorting
            })
        except Exception as e:
            print(f"Gagal membaca {filepath}: {e}")

    # Urutkan berdasarkan mtime terbaru (descending)
    comics.sort(key=lambda x: x['mtime'], reverse=True)

    # Hapus field mtime sebelum disimpan
    for comic in comics:
        del comic['mtime']

    # Simpan ke list2.json
    with open('list2.json', 'w', encoding='utf-8') as f:
        json.dump(comics, f, indent=4)

    print(f"✅ Berhasil membuat list.json dengan {len(comics)} komik (diurutkan update terbaru).")

if __name__ == "__main__":
    generate_list_from_db()
