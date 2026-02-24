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
    
    # 1. Load Data Lama (Logika Append)
    old_chapters_dict = {}
    old_thumb = ""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                # Simpan chapter lama dalam dictionary agar cepat dicari
                old_chapters_dict = {ch['nama']: ch for ch in old_data.get('chapters', [])}
                old_thumb = old_data.get('thumb', '')
                print(f"   [!] Database ditemukan. {len(old_chapters_dict)} chapter sudah tersimpan.")
        except: pass

    try:
        # Upload Sampul (Hanya jika belum ada di database)
        thumb_cloud = old_thumb
        if not thumb_cloud and thumb_url and "http" in thumb_url:
            try:
                up = cloudinary.uploader.upload(thumb_url, public_id=slug, folder="petomic_thumbs", overwrite=True)
                thumb_cloud = up['secure_url']
            except:
                thumb_cloud = thumb_url
        
        res = requests.get(link, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        ch_list_from_web = []

        # Ambil SEMUA daftar chapter dari elemen list
        # Selector ini lebih akurat untuk mengambil ribuan chapter sekaligus
        items = soup.select('ul.row-content-chapter li, .eplister li, select[name="nPL_list"] option')
        
        for item in items:
            if item.name == 'option':
                u = item.get('value')
                n = item.text.strip()
            else:
                a_tag = item.find('a')
                if not a_tag: continue
                u = a_tag['href']
                n = a_tag.text.strip()
            
            if u and "manhuaplus.org" in u:
                ch_list_from_web.append({"nama": n, "url": u})

        if not ch_list_from_web: return None
        
        # Balikkan urutan agar chapter terbaru ada di atas (index 0)
        # Sesuai kebiasaan ManhuaPlus yang menaruh chapter terbaru di atas
        
        # --- PERUBAHAN KRUSIAL: Filter Chapter Baru ---
        new_chapters_to_scrape = []
        for ch in ch_list_from_web:
            if ch['nama'] not in old_chapters_dict:
                new_chapters_to_scrape.append(ch)

        # Jika ada limit (untuk routine), potong list-nya
        if limit_ch:
            new_chapters_to_scrape = new_chapters_to_scrape[:limit_ch]

        print(f"   [+] Menemukan {len(new_chapters_to_scrape)} chapter baru untuk di-scrape.")

        # Scrape hanya chapter yang baru
        new_final_chapters = []
        for ch in new_chapters_to_scrape:
            print(f"   -> Scraping New Chapter: {ch['nama']}")
            imgs = get_images(ch['url'])
            if imgs:
                new_final_chapters.append({"nama": ch['nama'], "images": imgs})
            time.sleep(0.8)

        # Gabungkan Chapter Lama + Chapter Baru
        # Pastikan tidak ada duplikat dan urutannya benar
        for ch in new_final_chapters:
            old_chapters_dict[ch['nama']] = ch
        
        # Urutkan kembali berdasarkan logika (misal: Chapter 1 di awal JSON)
        # Atau biarkan apa adanya jika detail.html kamu sudah pakai .reverse()
        all_chapters = list(old_chapters_dict.values())

        # Simpan ke Database di Root
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "judul": judul, 
                "thumb": thumb_cloud, 
                "chapters": all_chapters
            }, f, indent=4)
        
        print(f"SUKSES: {slug}.json diperbarui. Total: {len(all_chapters)} chapter.")
        return {"judul": judul, "slug": slug, "thumb": thumb_cloud}
    except Exception as e:
        print(f"Gagal memproses {judul}: {e}")
        return None

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"https://manhuaplus.org/manga/{target_slug}"
        # Jika manual, scrape semua chapter baru yang ditemukan
        process_comic(target_slug.replace('-', ' ').title(), url, target_slug, "", limit_ch=None)
    else:
        print("Scraping katalog rutin PetoMic (Halaman 1)...")
        list_json = []
        # Untuk katalog rutin, cukup 1 halaman untuk update terbaru
        url_katalog = "https://manhuaplus.org/all-manga/"
        res = requests.get(url_katalog, headers=HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        items = soup.select('.listupd .bs, .page-item-detail')
        
        for item in items:
            try:
                link_tag = item.select_one('a')
                if not link_tag: continue
                
                judul = link_tag.get('title') or link_tag.text.strip()
                link = link_tag['href']
                slug = link.strip('/').split('/')[-1]
                
                img_tag = item.select_one('img')
                thumb = img_tag.get('data-src') or img_tag.get('src')
                
                # Update rutin hanya ambil 5 chapter terbaru per judul agar cepat
                hasil = process_comic(judul, link, slug, thumb, limit_ch=5)
                if hasil: 
                    list_json.append(hasil)
            except: continue
        
        # Update list.json di root
        with open('list.json', 'w', encoding='utf-8') as f:
            json.dump(list_json, f, indent=4)

if __name__ == "__main__":
    main()
