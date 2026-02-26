import os
import json
import glob

def generate_stats(db_folder='db', output_file='stats.json'):
    """
    Membaca semua file JSON di folder db, menghitung jumlah chapter,
    dan menyimpan komik dengan chapter < 20 ke stats.json.
    """
    # Cari semua file JSON di folder db
    json_files = glob.glob(os.path.join(db_folder, '*.json'))
    stats = []

    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Ambil slug dari nama file
            slug = os.path.splitext(os.path.basename(filepath))[0]
            judul = data.get('judul', slug)
            thumb = data.get('thumb', '')
            chapter_count = len(data.get('chapters', []))

            stats.append({
                'slug': slug,
                'judul': judul,
                'thumb': thumb,
                'chapterCount': chapter_count
            })
        except Exception as e:
            print(f"Error membaca {filepath}: {e}")

    # Filter komik dengan chapter < 20
    low_chapter = [c for c in stats if c['chapterCount'] < 20]

    # Simpan ke file stats.json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(low_chapter, f, indent=2, ensure_ascii=False)

    print(f"Total komik dengan chapter < 20: {len(low_chapter)}")
    print(f"Data disimpan di {output_file}")

if __name__ == "__main__":
    # Secara default membaca dari folder 'db' dan output ke 'stats.json'
    # Jika Anda menggunakan folder db2, ubah parameter db_folder='db2'
    generate_stats(db_folder='db', output_file='stats.json')
