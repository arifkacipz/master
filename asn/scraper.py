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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://manhuaplus.org/',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_images(chapter_url):
    """Mengambil daftar gambar dari sebuah chapter menggunakan AJAX."""
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
    except:
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    """Memproses komik dengan sistem Deep-Scrape untuk mengambil ribuan chapter."""
    print(f"\n--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    # 1. Load Database Lokal
    old_chapters_dict = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                print(f"   [!] Database Lokal: Terdeteksi {len(old_chapters_dict)} chapter.")
        except: pass

    try:
        # 2. Ambil Halaman Utama & Bongkar Manga ID (Kunci untuk Full List)
        res = requests.get(link, headers=HEADERS, timeout=20)
        
        # Mencoba 3 pola ID berbeda yang sering digunakan ManhuaPlus
        m_id_match = re.search(r'manga_id\s*:\s*["\'](\d+)["\']|data-id=["\'](\d+)["\']|chapter_list_manga_(\d+)', res.text)
        
        ch_list_from_web = []
        if m_id_match:
            m_id = m_id_match.group(1) or m_id_match.group(2) or m_id_match.group(3)
            print(f"   [+] Manga ID Ditemukan: {m_id}. Meminta daftar chapter lengkap...")
            
            # Jalur AJAX khusus untuk memintas batasan "20 chapter"
            ajax_urls = [
                f"https://manhuaplus.org/ajax/chapters/list?manga_id={m_id}",
                "https://manhuaplus.org/wp-admin/admin-ajax.php"
            ]
            
            for a_url in ajax_urls:
                if "admin-ajax" in a_url:
                    ajax_res = requests.post(a_url, headers=HEADERS, data={'action': 'manga_get_chapters', 'manga': m_id}, timeout=20)
                else:
                    ajax_res = requests.post(a_url, headers=HEADERS, timeout=20)
                
                if ajax_res.status_code == 200 and len(ajax_res.text) > 100:
                    soup_ch = BeautifulSoup(ajax_res.text, 'html.parser')
                    items = soup_ch.select('li')
                    for item in items:
                        a = item.find('a')
                        if a and '/chapters/' in a['href']:
                            ch_list_from_web.append({"nama": a.text.strip(), "url": a['href']})
                    if ch_list_from_web: break # Berhenti jika sudah dapat

        # Backup: Jika AJAX gagal, sikat semua selector HTML
        if not ch_list_from_web:
            print("   [!] AJAX Gagal. Menyisir HTML mentah...")
            soup = BeautifulSoup(res.text, 'html.parser')
            for sel in ['ul.row-content-chapter li', '.eplister li', '.cl li']:
                for item in soup.select(sel):
                    a = item.find('a')
                    if a and a.text.strip() not in [c['nama'] for c in ch_list_from_web]:
                        ch_list_from_web.append({"nama": a.text.strip(), "url": a['href']})

        print(f"   [?] Hasil: Scraper melihat {len(ch_list_from_web)} chapter di web.")

        # 3. Bandingkan: Apa ada yang baru/hilang?
        new_chapters = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]
        
        if not new_chapters:
            print(f"   [~] Selesai: Semua {len(ch_list_from_web)} chapter di web sudah ada di database.")
            return {"judul": judul, "slug": slug, "thumb": thumb_url}

        # Urutkan agar Chapter lama diproses duluan (Ch 1, 2, dst)
        new_chapters.reverse()

        if limit_ch:
            new_chapters = new_chapters[:limit_ch]

        print(f"   [+] Memulai scraping {len(new_chapters)} chapter baru...")

        for ch in new_chapters:
            print(f"   -> Mendownload Gambar: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1)

        # 4. Simpan Database dengan Urutan Rapi
        all_chapters = list(old_chapters_dict.values())
        try:
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except: pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": thumb_url, "chapters": all_chapters}, f, indent=4)
        
        print(f"DONE: {slug}.json kini memiliki {len(all_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": thumb_url}
    except Exception as e:
        print(f"Error fatal: {e}")
        return None

def main():
    """Fungsi kontrol untuk mode Manual (TARGET_SLUG) atau Rutin."""
    target_slug = os.environ.get('TARGET_SLUG')
    
    if target_slug:
        # MODE MANUAL: Ambil seluruh daftar chapter
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        # MODE RUTIN: Update katalog utama
        print("Scraping katalog rutin...")
        list_json = []
        for page in range(1, 4):
            url_katalog = "https://manhuaplus.org/all-manga/" if page == 1 else f"https://manhuaplus.org/all-manga/{page}/?sort=last_update"
            try:
                res = requests.get(url_katalog, headers=HEADERS, timeout=20)
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select('.listupd .bs, .page-item-detail, .mh-77vh > div')
                for item in items:
                    link_tag = item.select_one('a')
                    if not link_tag: continue
                    judul = link_tag.get('title') or link_tag.text.strip()
                    link = link_tag['href']
                    slug = link.strip('/').split('/')[-1]
                    img_tag = item.select_one('img')
                    thumb = img_tag.get('data-src') or img_tag.get('src') if img_tag else ""
                    
                    hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
                    if hasil: list_json.append(hasil)
            except: continue
        
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
