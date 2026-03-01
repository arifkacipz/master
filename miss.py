import os
import json

def update_missing():
    db_folder = 'db'
    if not os.path.exists(db_folder):
        print("Folder db tidak ditemukan")
        return

    missing_list = []
    # Membaca semua file JSON di folder db
    for filename in os.listdir(db_folder):
        if not filename.endswith('.json'):
            continue
        slug = filename[:-5]
        path = os.path.join(db_folder, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Gagal membaca {filename}: {e}")
            continue

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

    with open('missing.json', 'w', encoding='utf-8') as f:
        json.dump(missing_list, f, indent=2)
    print(f"missing.json diperbarui dengan {len(missing_list)} komik.")

if __name__ == "__main__":
    update_missing()
