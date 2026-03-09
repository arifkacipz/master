import os
import json

def update_missing(db_folder='db', output_file='missing.json'):
    """
    Membaca semua file JSON di folder db (termasuk subfolder),
    dan menghasilkan laporan missing.json berdasarkan data terkini.
    """
    if not os.path.exists(db_folder):
        print(f"Folder {db_folder} tidak ditemukan")
        return

    missing_list = []

    # Gunakan os.walk untuk memindai semua subfolder
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

            slug = os.path.splitext(filename)[0]  # slug dari nama file
            judul = data.get('judul', slug)
            thumb = data.get('thumb', '')
            online = data.get('online', 0)
            chs = data.get('Chs', '')
            chapters = data.get('chapters', [])

            # Daftar nama chapter lokal
            local_names = [ch.get('nama', '') for ch in chapters if ch.get('nama')]

            # Parsing Chs menjadi list nama online
            online_names = [name.strip() for name in chs.split(',') if name.strip()] if chs else []

            if online == 0 or not online_names:
                # Data tidak lengkap, lewati
                continue

            # Cari chapter yang hilang
            missing_names = [name for name in online_names if name not in local_names]

            if missing_names:
                missing_list.append({
                    'slug': slug,
                    'judul': judul,
                    'thumb': thumb,
                    'total_online': online,
                    'total_downloaded': len(local_names),
                    'missing': missing_names
                })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(missing_list, f, indent=2, ensure_ascii=False)

    print(f"missing.json diperbarui dengan {len(missing_list)} komik.")

if __name__ == "__main__":
    update_missing(db_folder='db', output_file='missing.json')
