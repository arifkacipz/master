import os
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
import random

BASE_URL = "https://asuracomic.net"

# Buat scraper dengan cloudscraper
scraper = cloudscraper.create_scraper()
scraper.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://asuracomic.net/',
    'Connection': 'keep-alive',
})

def get_soup(url):
    """Mengambil dan memparsing halaman HTML dengan jeda acak"""
    try:
        time.sleep(random.uniform(1, 2))
        res = scraper.get(url, timeout=20)
        res.raise_for_status()
        return BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_json_data(html):
    """Mengekstrak data JSON dari tag script __NEXT_DATA__"""
    soup = BeautifulSoup(html, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if script_tag:
        try:
            return json.loads(script_tag.string)
        except:
            return None
    return None

def get_series_list(page=1):
    url = f"{BASE_URL}/series?page={page}"
    soup = get_soup(url)
    if not soup:
        return []
    
    series = []
    items = soup.select('a[href^="/series/"]')
    
    seen_slugs = set()
    for a in items:
        link = a.get('href')
        if not link or not link.startswith('/series/'):
            continue
        slug = link.split('/')[-1]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        
        full_link = BASE_URL + link
        
        title_elem = a.select_one('span.block.text-\\[13\\.3px\\].font-bold')
        if not title_elem:
            title_elem = a.select_one('div[class*="font-bold"]')
        judul = title_elem.text.strip() if title_elem else slug.replace('-', ' ').title()
        
        img = a.select_one('img')
        thumb = ''
        if img:
            thumb = img.get('src') or img.get('data-src') or ''
            if thumb and not thumb.startswith('http'):
                thumb = BASE_URL + thumb
        
        series.append({
            'judul': judul,
            'link': full_link,
            'slug': slug,
            'thumb': thumb
        })
    
    return series

def get_chapters_from_detail(series_url, limit=None):
    soup = get_soup(series_url)
    if not soup:
        return []
    
    chapters = []
    # Coba dari JSON
    json_data = extract_json_data(str(soup))
    if json_data:
        try:
            props = json_data.get('props', {}).get('pageProps', {})
            chapters_data = props.get('chapters', [])
            if chapters_data:
                if limit:
                    chapters_data = chapters_data[:limit]
                for ch in chapters_data:
                    chap_num = ch.get('name', '')
                    chap_url = f"{series_url}/chapter/{chap_num}"
                    chap_name = f"Chapter {chap_num}"
                    if ch.get('title'):
                        chap_name += f" - {ch['title']}"
                    chapters.append({
                        'nama': chap_name,
                        'url': chap_url
                    })
                return chapters
        except Exception as e:
            print(f"Error parsing chapters JSON: {e}")
    
    # Fallback HTML
    chapter_container = soup.select_one('div.pl-4.pr-2.pb-4.overflow-y-auto')
    if chapter_container:
        chapter_links = chapter_container.select('a[href*="/chapter/"]')
        if limit:
            chapter_links = chapter_links[:limit]
        for a in chapter_links:
            href = a.get('href')
            if not href:
                continue
            if href.startswith('/'):
                chapter_url = BASE_URL + href
            else:
                chapter_url = BASE_URL + '/' + href
            
            nama_elem = a.select_one('h3.text-sm.text-white.font-medium')
            nama = nama_elem.text.strip() if nama_elem else href.split('/')[-1]
            chapters.append({
                'nama': nama,
                'url': chapter_url
            })
    
    return chapters

def get_images_from_chapter_page(chapter_url):
    """Mengambil semua URL gambar dari halaman chapter"""
    try:
        res = scraper.get(chapter_url, timeout=20)
        if res.status_code != 200:
            print(f"   [Error] Status code {res.status_code} for {chapter_url}")
            return []
    except Exception as e:
        print(f"   [Error] Exception fetching {chapter_url}: {e}")
        return []
    
    # Coba ekstrak dari JSON
    json_data = extract_json_data(res.text)
    if json_data:
        try:
            props = json_data.get('props', {}).get('pageProps', {})
            # Coba path: props.chapter.pages
            chapter_data = props.get('chapter', {})
            pages = chapter_data.get('pages', [])
            if pages:
                images = []
                for page in pages:
                    if isinstance(page, dict):
                        img_url = page.get('url') or page.get('src')
                        if img_url:
                            images.append(img_url)
                    elif isinstance(page, str):
                        images.append(page)
                if images:
                    return images
        except Exception as e:
            print(f"   [Error parsing JSON: {e}")
    
    # Fallback ke parsing HTML
    soup = BeautifulSoup(res.text, 'html.parser')
    images = []
    # Cari semua img dengan src yang mengandung domain storage
    for img in soup.select('img[src*="gg.asuracomic.net/storage/media"]'):
        src = img.get('src')
        if src and src not in images:
            images.append(src)
    # Juga coba data-src (untuk lazy loading)
    for img in soup.select('img[data-src*="gg.asuracomic.net/storage/media"]'):
        src = img.get('data-src')
        if src and src not in images:
            images.append(src)
    
    if images:
        return images
    else:
        print(f"   [Warning] No images found for {chapter_url}")
        return []

def merge_chapters(old_chapters, new_chapters):
    combined = {ch['url']: ch for ch in old_chapters if 'url' in ch}
    for ch in new_chapters:
        combined[ch['url']] = ch
    merged = list(combined.values())
    
    def get_ch_number(ch):
        match = re.search(r'(\d+(?:\.\d+)?)', ch['nama'])
        return float(match.group(1)) if match else 0
    merged.sort(key=get_ch_number)
    return merged

def process_comic(comic, limit_ch=None):
    judul = comic['judul']
    link = comic['link']
    slug = comic['slug']
    thumb = comic['thumb']
    
    print(f"--- Memproses: {judul} ---")
    
    chapters = get_chapters_from_detail(link, limit=limit_ch)
    if not chapters:
        print(f"Tidak ada chapter untuk {slug}")
        return None
    
    print(f"   -> Ditemukan {len(chapters)} chapter")
    
    final_chapters = []
    for i, ch in enumerate(chapters):
        print(f"   -> Scraping {ch['nama']} ({i+1}/{len(chapters)})")
        images = get_images_from_chapter_page(ch['url'])
        if images:
            final_chapters.append({
                'nama': ch['nama'],
                'url': ch['url'],
                'images': images
            })
        time.sleep(random.uniform(1, 2))
    
    if not final_chapters:
        print(f"Tidak ada gambar untuk {slug}")
        return None
    
    # Urutkan chapter berdasarkan nomor
    final_chapters.sort(key=lambda ch: float(re.search(r'(\d+(?:\.\d+)?)', ch['nama']).group(1)) if re.search(r'(\d+(?:\.\d+)?)', ch['nama']) else 0)
    
    # Gabung dengan data lama jika ada
    db_path = f'db2/{slug}.json'
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            old_chapters = old_data.get('chapters', [])
            old_valid = [ch for ch in old_chapters if 'url' in ch]
            final_chapters = merge_chapters(old_valid, final_chapters)
            print(f"   -> Menggabungkan dengan {len(old_valid)} chapter lama")
        except Exception as e:
            print(f"   -> Gagal membaca file lama ({e}), akan menimpa")
    
    os.makedirs('db2', exist_ok=True)
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump({
            'judul': judul,
            'thumb': thumb,
            'chapters': final_chapters
        }, f, indent=4)
    
    print(f"SUKSES: {slug}.json tersimpan di db2/ ({len(final_chapters)} chapter)")
    return {'judul': judul, 'slug': slug, 'thumb': thumb}

def main():
    target_slug = os.environ.get('TARGET_SLUG')
    if target_slug:
        url = f"{BASE_URL}/series/{target_slug}"
        soup = get_soup(url)
        if not soup:
            print("Gagal mengakses halaman komik")
            return
        
        judul = target_slug.replace('-', ' ').title()
        json_data = extract_json_data(str(soup))
        if json_data:
            try:
                props = json_data.get('props', {}).get('pageProps', {})
                comic_data = props.get('comic', {})
                if comic_data and 'name' in comic_data:
                    judul = comic_data['name']
            except:
                pass
        
        thumb = ""
        og_img = soup.find('meta', property='og:image')
        if og_img and og_img.get('content'):
            thumb = og_img['content']
        else:
            img_tag = soup.select_one('img[src*="storage/media"]')
            if img_tag:
                thumb = img_tag.get('src') or ''
        
        comic = {'judul': judul, 'link': url, 'slug': target_slug, 'thumb': thumb}
        result = process_comic(comic, limit_ch=None)
        if result:
            with open('list2.json', 'w', encoding='utf-8') as f:
                json.dump([result], f, indent=4)
            print("Katalog disimpan sebagai list2.json")
    else:
        # Mode katalog: hanya halaman 1 untuk testing
        all_comics = []
        for page in range(1, 2):
            print(f"\n--- Halaman {page} ---")
            comics = get_series_list(page)
            if not comics:
                break
            print(f"Ditemukan {len(comics)} komik")
            all_comics.extend(comics)
            time.sleep(random.uniform(2, 3))
        
        results = []
        for i, comic in enumerate(all_comics):
            print(f"\nProgress: {i+1}/{len(all_comics)}")
            res = process_comic(comic, limit_ch=2)
            if res:
                results.append(res)
            time.sleep(random.uniform(2, 3))
        
        with open('list2.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        print(f"\nSelesai. Total {len(results)} komik diproses. Katalog disimpan sebagai list2.json")

if __name__ == "__main__":
    main()
