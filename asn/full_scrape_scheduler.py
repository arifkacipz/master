import os
import json
import time
import glob
from scraper import process_comic  # pastikan scraper.py ada di folder yang sama

TRACKER_FILE = 'full_scrape_tracker.json'

def get_all_slugs():
    """Ambil semua slug dari file JSON di folder db/"""
    json_files = glob.glob('db/*.json')
    return [os.path.splitext(os.path.basename(f))[0] for f in json_files]

def load_tracker():
    """Baca tracker, jika belum ada buat dictionary kosong"""
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tracker(tracker):
    """Simpan tracker ke file"""
    with open(TRACKER_FILE, 'w') as f:
        json.dump(tracker, f, indent=2)

def select_slug(slugs, tracker):
    """
    Pilih satu slug untuk diproses:
    - Prioritas: slug yang belum pernah di‑full‑scrape (slug baru)
    - Jika semua sudah pernah, kembalikan None (tidak ada yang perlu diproses)
    """
    slugs_set = set(slugs)
    tracked_set = set(tracker.keys())
    new_slugs = slugs_set - tracked_set
    if new_slugs:
        # Ambil slug baru pertama (urut abjad agar konsisten)
        return sorted(new_slugs)[0]
    # Semua sudah pernah diproses
    return None

def main():
    slugs = get_all_slugs()
    if not slugs:
        print("Tidak ada komik di folder db/")
        return

    tracker = load_tracker()
    target = select_slug(slugs, tracker)

    if target is None:
        print("Semua slug sudah pernah di‑full‑scrape. Tidak ada yang perlu diproses.")
        return

    print(f"Memproses full scrape untuk: {target}")

    # Ambil judul dari file JSON yang sudah ada (untuk logging)
    try:
        with open(f'db/{target}.json', 'r') as f:
            judul = json.load(f).get('judul', target)
    except:
        judul = target

    url = f"https://manhuaplus.org/manga/{target}"
    hasil = process_comic(judul, url, target, thumb_url=None, limit_ch=None)

    # Update tracker (apapun hasilnya, agar tidak terus menerus mencoba slug yang gagal)
    tracker[target] = time.time()
    save_tracker(tracker)

    if hasil:
        print(f"✅ {target} sukses")
    else:
        print(f"❌ {target} gagal")

if __name__ == "__main__":
    main()
