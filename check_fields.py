import os
import json

def check_missing_fields():
    db_folder = 'db'
    report = []
    
    if not os.path.exists(db_folder):
        print(f"Folder {db_folder} tidak ditemukan.")
        return
    
    # Loop semua file JSON di folder db
    for filename in os.listdir(db_folder):
        if not filename.endswith('.json'):
            continue
        slug = filename[:-5]
        path = os.path.join(db_folder, filename)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error membaca {filename}: {e}")
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
    output_file = 'missing_fields.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"Laporan disimpan di {output_file}")
    print(f"Total file dengan field hilang: {len(report)}")

if __name__ == '__main__':
    check_missing_fields()
