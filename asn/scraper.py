import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

# 1. KONFIGURASI CLOUDINARY
cloudinary.config(
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key = os.environ.get('CLOUDINARY_API_KEY'),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
}

def get_images(chapter_url):
    """Mengambil gambar chapter dengan sistem AJAX."""
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
        if ajax_res.status_code == 200:
            data = ajax_res.json()
            if data.get('status') and 'html' in data:
                html_content = data['html']
                list_gambar = re.findall(r'https?://cdn\.manhuaplus\.cc/[^\s"\']+', html_content)
                temp_list = []
                seen = set()
                for img in list_gambar:
                    img = img.strip()
                    if "loading.gif" not in img and img not in seen:
                        temp_list.append(img)
                        seen.add(img)
                temp_list.sort()
                return temp_list
        return []
    except: return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    """Proses komik dengan perbaikan nama chapter otomatis."""
    print(f"\n--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    old_chapters_dict = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                # Normalisasi nama lama agar perbandingan akurat
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                print(f"   [!] Database Lokal: Terdeteksi {len(old_chapters_dict)} chapter.")
        except: pass

    try:
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list_from_web = []

        # METODE 1: JSON-LD (Prioritas Nama Chapter Asli)
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                js_data = json.loads(s.string)
                graph = js_data.get('@graph', [js_data])
                for g in graph:
                    if g.get('@type') == 'ItemList':
                        for item in g.get('itemListElement', []):
                            u = item.get('url')
                            n = item.get('name') # Ambil field 'name' resmi
                            if u and '/chapters/' in u:
                                # Jika nama berupa angka ID, bersihkan
                                if not n or n.isdigit():
                                    # Coba ambil angka terakhir dari URL sebagai nomor chapter
                                    num_match = re.findall(r'\d+', u.split('/')[-1])
                                    n = f"Chapter {num_match[-1]}" if num_match else n
                                ch_list_from_web.append({"nama": n, "url": u})
            except: continue

        # METODE 2: AJAX Fallback
        if not ch_list_from_web:
            m_id = re.search(r'manga_id\s*:\s*["\'](\d+)["\']|data-id=["\'](\d+)["\']', res.text)
            if m_id:
                manga_id = m_id.group(1) or m_id.group(2)
                ajax_url = f"https://manhuaplus.org/ajax/chapters/list?manga_id={manga_id}"
                ajax_res = requests.post(ajax_url, headers=HEADERS, timeout=20)
                if ajax_res.status_code == 200:
                    soup_ch = BeautifulSoup(ajax_res.text, 'html.parser')
                    for a in soup_ch.find_all('a'):
                        if '/chapters/' in a.get('href', ''):
                            ch_list_from_web.append({"nama": a.text.strip(), "url": a['href']})

        print(f"   [?] Hasil: Scraper melihat {len(ch_list_from_web)} chapter di web.")

        # Filter: Hanya ambil yang benar-benar baru berdasarkan nama
        new_chapters = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]
        
        if not new_chapters:
            print(f"   [~] Semua {len(ch_list_from_web)} chapter sudah tersimpan.")
            return {"judul": judul, "slug": slug, "thumb": thumb_url}

        new_chapters.reverse() 
        if limit_ch: new_chapters = new_chapters[:limit_ch]

        print(f"   [+] Memulai scrape {len(new_chapters)} chapter baru...")

        for ch in new_chapters:
            print(f"   -> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1.2)

        # Sorting Numerik
        all_chapters = list(old_chapters_dict.values())
        try:
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except: pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_url, "chapters": all_chapters}, f, indent=4)
        
        print(f"DONE: {slug}.json diperbarui menjadi {len(all_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": thumb_url}
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Scraping katalog rutin...")
        list_json = []
        for page in range(1, 4):
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update"
            try:
                res = requests.get(url_katalog, headers=HEADERS, timeout=20)
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('.listupd .bs, .page-item-detail, .mh-77vh > div')
                for item in items:
                    a = item.select_one('a')
                    if not a: continue
                    judul = a.get('title') or a.text.strip()
                    link = a['href']
                    slug = link.strip('/').split('/')[-1]
                    img = item.select_one('img')
                    thumb = img.get('data-src') or img.get('src') if img else ""
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
                    if hasil: list_json.append(hasil)
            except: continue
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
