import os
import json

def check_missing_fields(db_folder='db', output_file='missing_fields.json'):
    """
    Memeriksa semua file JSON di folder db (termasuk subfolder)
    untuk field yang hilang (source, online, Chs).
    """
    if not os.path.exists(db_folder):
        print(f"Folder {db_folder} tidak ditemukan.")
        return
    
    report = []
    
    # Gunakan os.walk untuk memindai semua subfolder
    for root, dirs, files in os.walk(db_folder):
        for filename in files:
            if not filename.endswith('.json'):
                continue
            slug = os.path.splitext(filename)[0]
            filepath = os.path.join(root, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error membaca {filepath}: {e}")
                continue
            
            # Cek field yang diperlukan
            missing = []
            if 'source' not in data:
                missing.append('source')
            if 'online' not in data:
                missing.append('online')
            if 'Chs' not in data:
                missing.append('Chs')
            
            # Jika ada field yang hilang, tambahkan ke laporan
            if missing:
                report.append({
                    'slug': slug,
                    'judul': data.get('judul', slug),
                    'missing_fields': missing
                })
    
    # Simpan laporan ke file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Laporan disimpan di {output_file}")
    print(f"Total file dengan field hilang: {len(report)}")

if __name__ == '__main__':
    check_missing_fields(db_folder='db', output_file='missing_fields.json')
