import os
import json
import time
import subprocess
from scraper import process_comic  # pastikan scraper.py ada di folder yang sama

TRACKER_FILE = 'full_scrape_tracker.json'
STATS_FILE = 'stats.json'

def get_slugs_from_stats():
    """Ambil semua slug dari file stats.json"""
    if not os.path.exists(STATS_FILE):
        print(f"File {STATS_FILE} tidak ditemukan.")
        return []
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
        # data adalah list objek dengan field 'slug'
        return [item['slug'] for item in data if 'slug' in item]
    except Exception as e:
        print(f"Gagal membaca {STATS_FILE}: {e}")
        return []

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
    - Jika semua sudah pernah, pilih slug dengan timestamp terlama (paling lama tidak di‑scrape)
    """
    slugs_set = set(slugs)
    tracked_set = set(tracker.keys())
    new_slugs = slugs_set - tracked_set
    if new_slugs:
        # Ambil slug baru pertama (urut abjad agar konsisten)
        return sorted(new_slugs)[0]
    # Semua sudah pernah diproses, pilih yang paling lama (timestamp terkecil)
    if slugs_set:
        oldest_slug = min(slugs_set, key=lambda s: tracker.get(s, float('inf')))
        return oldest_slug
    return None

def main():
    slugs = get_slugs_from_stats()
    if not slugs:
        print("Tidak ada slug di stats.json.")
        return

    tracker = load_tracker()
    target = select_slug(slugs, tracker)

    if target is None:
        print("Tidak ada slug yang dapat diproses.")
        return

    print(f"Memproses full scrape untuk: {target}")

    # Ambil judul dari file JSON di db/ (untuk logging)
    try:
        with open(f'db/{target}.json', 'r') as f:
            judul = json.load(f).get('judul', target)
    except:
        judul = target

    url = f"https://manhuaplus.org/manga/{target}"
    hasil = process_comic(judul, url, target, thumb_url=None, limit_ch=None)

    # Update tracker (apapun hasilnya)
    tracker[target] = time.time()
    save_tracker(tracker)

    if hasil:
        print(f"✅ {target} sukses")
    else:
        print(f"❌ {target} gagal")

    # Jalankan generate_stats.py untuk memperbarui stats.json
    print("Menjalankan generate_stats.py...")
    try:
        subprocess.run(["python", "generate_stats.py"], check=True)
        print("generate_stats.py selesai.")
    except Exception as e:
        print(f"Gagal menjalankan generate_stats.py: {e}")

if __name__ == "__main__":
    main()
