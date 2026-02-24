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

# Menyamar sebagai Chrome di Android (Sesuai tampilan HP Anda)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://manhuaplus.org/',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

def get_images(chapter_url):
    """Mengambil gambar chapter dengan proteksi referer."""
    try:
        chapter_id = chapter_url.strip('/').split('/')[-1]
        if not chapter_id.isdigit():
            res = requests.get(chapter_url, headers=HEADERS, timeout=20)
            match = re.search(r'CHAPTER_ID\s*=\s*(\d+)', res.text)
            if match: chapter_id = match.group(1)
            else: return []

        ajax_url = f"https://manhuaplus.org/ajax/image/list/chap/{chapter_id}"
        # Kirim request dengan referer spesifik chapter
        current_headers = HEADERS.copy()
        current_headers['Referer'] = chapter_url
        
        ajax_res = requests.post(ajax_url, headers=current_headers, timeout=20)
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
    """Proses komik dengan pendeteksi chapter berbasis JSON-LD (Anti-Skip)."""
    print(f"\n--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    old_chapters_dict = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                print(f"   [!] Database Lokal: Terdeteksi {len(old_chapters_dict)} chapter.")
        except: pass

    try:
        res = requests.get(link, headers=HEADERS, timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list_from_web = []

        # METODE 1: JSON-LD (Paling Akurat untuk 10.000 Chapter)
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                js_data = json.loads(s.string)
                # Mencari @graph yang berisi daftar ItemList
                graph = js_data.get('@graph', [js_data])
                for g in graph:
                    if g.get('@type') == 'ItemList':
                        for item in g.get('itemListElement', []):
                            u = item.get('url')
                            if u and '/chapters/' in u:
                                # Ambil nama dari URL jika teks tidak ada
                                n = u.strip('/').split('/')[-1].replace('-', ' ').title()
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

        # METODE 3: Greedy Search (Menyisir Link)
        if not ch_list_from_web:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if '/chapters/' in href and slug in href:
                    name = a.text.strip() or href.split('/')[-1]
                    if href not in [c['url'] for c in ch_list_from_web]:
                        ch_list_from_web.append({"nama": name, "url": href})

        print(f"   [?] Hasil: Scraper melihat {len(ch_list_from_web)} chapter di web.")

        # Filter Chapter Baru
        new_chapters = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]
        
        if not new_chapters:
            print(f"   [~] Semua {len(ch_list_from_web)} chapter sudah tersimpan.")
            return {"judul": judul, "slug": slug, "thumb": thumb_url}

        new_chapters.reverse() # Proses dari Chapter 1 ke atas
        if limit_ch: new_chapters = new_chapters[:limit_ch]

        print(f"   [+] Memulai scrape {len(new_chapters)} chapter baru (termasuk chapter lama yang terskip)...")

        for ch in new_chapters:
            print(f"   -> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1.2) # Jeda lebih lama agar tidak dicurigai

        # Sorting Numerik Rapi
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
