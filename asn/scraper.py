import os
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import cloudinary
import cloudinary.uploader

# Konfigurasi Cloudinary
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
    except Exception as e:
        print(f"Error get_images: {e}")
        return []

def process_comic(judul, link, slug, thumb_url, limit_ch=None):
    print(f"--- PetoMic memproses: {judul} ---")
    filepath = f'db/{slug}.json'
    os.makedirs('db', exist_ok=True)
    
    old_chapters_dict = {}
    old_thumb = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                old_thumb = old_data.get('thumb', '')
                print(f"   [!] Database ditemukan: {len(old_chapters_dict)} chapter tersimpan.")
        except: pass

    try:
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list_from_web = []

        # Mencari semua link chapter di halaman komik
        items = soup.select('ul.row-content-chapter li, .eplister li, .cl li')
        for item in items:
            a_tag = item.find('a')
            if a_tag and 'href' in a_tag.attrs:
                u = a_tag['href']
                n = a_tag.text.strip()
                if "/chapters/" in u:
                    ch_list_from_web.append({"nama": n, "url": u})

        # Filter chapter yang benar-benar baru
        new_chapters_to_scrape = [ch for ch in ch_list_from_web if ch['nama'] not in old_chapters_dict]

        if limit_ch:
            new_chapters_to_scrape = new_chapters_to_scrape[:limit_ch]

        if not new_chapters_to_scrape:
            print("   [~] Tidak ada chapter baru.")
            return {"judul": judul, "slug": slug, "thumb": old_thumb or thumb_url}

        print(f"   [+] Menemukan {len(new_chapters_to_scrape)} chapter baru untuk di-scrape.")

        for ch in new_chapters_to_scrape:
            print(f"   -> Scraping: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                old_chapters_dict[ch['nama']] = {"nama": ch['nama'], "images": imgs}
            time.sleep(1)

        # Menggabungkan semua dan urutkan agar Chapter 1 di paling bawah (index awal)
        all_chapters = list(old_chapters_dict.values())
        try:
            all_chapters.sort(key=lambda x: float(re.findall(r"[-+]?\d*\.\d+|\d+", x['nama'])[0]))
        except: pass

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"judul": judul, "thumb": old_thumb or thumb_url, "chapters": all_chapters}, f, indent=4)
        
        print(f"SUKSES: {slug}.json diperbarui. Total: {len(all_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": old_thumb or thumb_url}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        # MODE MANUAL: Scrape semua chapter untuk satu komik
        url = f"https://manhuaplus.org/manga/{target_slug}"
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        # MODE RUTIN: Update katalog dari Halaman 1-3
        print("Scraping katalog rutin PetoMic...")
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
        print(f"Selesai! {len(list_json)} komik di katalog.")

if __name__ == "__main__":
    main()
