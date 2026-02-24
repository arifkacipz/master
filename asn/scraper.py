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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    """Fungsi standar untuk mengambil gambar."""
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
    print(f"\n--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    # 1. LOAD & BERSIHKAN DATABASE LAMA
    old_chapters_dict = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                # HANYA simpan chapter yang namanya BENAR (mengandung angka kecil, bukan ID ribuan)
                for ch in old_data.get('chapters', []):
                    # Jika nama chapter mengandung ID ribuan (seperti 92922), kita BUANG
                    if not re.search(r'Chapter\s\d{4,}', ch['nama']):
                        old_chapters_dict[ch['nama']] = ch
                print(f"   [!] Database dibersihkan. {len(old_chapters_dict)} chapter valid tersisa.")
        except: pass

    try:
        # 2. CARI MANGA ID DARI HALAMAN UTAMA
        res = requests.get(link, headers=HEADERS, timeout=25)
        m_id_match = re.search(r'manga_id\s*:\s*["\'](\d+)["\']|data-id=["\'](\d+)["\']', res.text)
        
        ch_list_from_web = []
        if m_id_match:
            manga_id = m_id_match.group(1) or m_id_match.group(2)
            print(f"   [+] ID: {manga_id}. Mengambil FULL LIST via AJAX Admin...")
            
            # Jalur paling kuat: admin-ajax.php
            ajax_url = "https://manhuaplus.org/wp-admin/admin-ajax.php"
            payload = {'action': 'manga_get_chapters', 'manga': manga_id}
            
            ajax_res = requests.post(ajax_url, headers=HEADERS, data=payload, timeout=20)
            if ajax_res.status_code == 200:
                soup_ch = BeautifulSoup(ajax_res.text, 'html.parser')
                items = soup_ch.select('li')
                for item in items:
                    a = item.find('a')
                    if a and '/chapters/' in a['href']:
                        # LOGIKA PENAMAAN BARU: Ambil dari teks link, jika angka ID, cari di URL
                        raw_name = a.text.strip()
                        url_part = a['href'].strip('/').split('/')[-1]
                        
                        # Jika teks berisi ID angka (seperti 92922), ekstrak nomor chapter dari URL
                        if raw_name.isdigit() or len(raw_name) < 2:
                            num_match = re.search(r'chapter-(\d+)', url_part)
                            final_name = f"Chapter {num_match.group(1)}" if num_match else f"Chapter {raw_name}"
                        else:
                            final_name = raw_name
                        
                        ch_list_from_web.append({"nama": final_name, "url": a['href']})

        # 3. FILTER & SCRAPE CHAPTER BARU
        new_chapters = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]
        print(f"   [?] Hasil: Web punya {len(ch_list_from_web)} chapter. Perlu scrape: {len(new_chapters)}")

        if not new_chapters:
            print("   [~] Database sudah lengkap dan bersih.")
            return {"judul": judul, "slug": slug, "thumb": thumb_url}

        # Urutkan Chapter 1 dulu
        new_chapters.reverse() 
        if limit_ch: new_chapters = new_chapters[:limit_ch]

        for ch in new_chapters:
            print(f"   -> Scraping Benar: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1)

        # 4. SIMPAN DENGAN SORTING RAPI
        all_chapters = list(old_chapters_dict.values())
        try:
            # Sortir berdasarkan angka di nama chapter
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except: pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_url, "chapters": all_chapters}, f, indent=4)
        
        print(f"DONE: {slug}.json kini memiliki {len(all_chapters)} chapter valid.")
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
        # Rutin update halaman 1
        list_json = []
        try:
            res = requests.get("https://manhuaplus.org/all-manga/", headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('.listupd .bs')
            for item in items:
                a = item.select_one('a')
                if not a: continue
                slug = a['href'].strip('/').split('/')[-1]
                hasil = process_comic(a.get('title', slug), a['href'], slug, "", limit_ch=5)
                if hasil: list_json.append(hasil)
            with open('list.json', 'w', encoding='utf-8') as f:
                json.dump(list_json, f, indent=4)
        except: pass

if __name__ == "__main__":
    main()
