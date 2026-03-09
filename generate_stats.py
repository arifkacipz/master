import os
import json

def generate_stats(db_folder='db', output_file='stats.json'):
    """
    Membaca semua file JSON di folder db (termasuk subfolder), menghitung jumlah chapter,
    dan menyimpan komik dengan chapter < 15 ke stats.json.
    """
    stats = []

    # Gunakan os.walk untuk memindai semua subfolder
    for root, dirs, files in os.walk(db_folder):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Ambil slug dari nama file (tanpa ekstensi)
                slug = os.path.splitext(filename)[0]
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

    # Filter komik dengan chapter < 15
    low_chapter = [c for c in stats if c['chapterCount'] < 15]

    # Simpan ke file stats.json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(low_chapter, f, indent=2, ensure_ascii=False)

    print(f"Total komik dengan chapter < 15: {len(low_chapter)}")
    print(f"Data disimpan di {output_file}")

if __name__ == "__main__":
    # Secara default membaca dari folder 'db' dan output ke 'stats.json'
    generate_stats(db_folder='db', output_file='stats.json')
