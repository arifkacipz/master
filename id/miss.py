import os
import json

def update_missing(db_folder='id/db', output_file='id/missing.json'):
    """
    Memindai semua file JSON di folder db (termasuk subfolder),
    dan menghasilkan laporan missing.json berdasarkan data terkini.
    Chapter dianggap "downloaded" jika memiliki setidaknya 1 gambar (images tidak kosong).
    """
    if not os.path.exists(db_folder):
        print(f"Folder {db_folder} tidak ditemukan")
        return

    missing_list = []

    for root, dirs, files in os.walk(db_folder):
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

            slug = os.path.splitext(filename)[0]
            judul = data.get('judul', slug)
            thumb = data.get('thumb', '')
            online = data.get('online', 0)          # total chapter online (dari Chs)
            chs = data.get('Chs', '')                # string nama chapter dipisah koma
            chapters = data.get('chapters', [])

            # Nama chapter yang sudah memiliki gambar (downloaded)
            downloaded_names = [ch['nama'] for ch in chapters if ch.get('images')]

            # Daftar nama chapter online dari Chs
            online_names = [name.strip() for name in chs.split(',') if name.strip()] if chs else []

            if online == 0 or not online_names:
                continue

            # Cari chapter yang belum didownload (tidak ada di downloaded_names)
            missing_names = [name for name in online_names if name not in downloaded_names]

            if missing_names:
                missing_list.append({
                    'slug': slug,
                    'judul': judul,
                    'thumb': thumb,
                    'total_online': online,
                    'total_downloaded': len(downloaded_names),
                    'missing': missing_names
                })

    # Simpan ke output_file (pastikan folder id/ ada)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(missing_list, f, indent=2, ensure_ascii=False)

    print(f"missing.json diperbarui dengan {len(missing_list)} komik yang memiliki chapter hilang.")

if __name__ == "__main__":
    update_missing()
