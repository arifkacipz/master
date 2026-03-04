# --- METODE 1: AJAX ---
# ... (kode AJAX) ...
if temp_list:
    if use_selenium:
        if not check_image_url(temp_list[0]):
            print("   Gambar pertama dari AJAX gagal, mencoba Selenium...")
            selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
            if selenium_imgs:
                return selenium_imgs
            else:
                print("   Selenium tidak menghasilkan gambar, tetap pakai hasil AJAX.")
    return temp_list

# --- METODE 2: Fallback HTML ---
fallback_images = get_images_manhuaplus_fallback(chapter_url)
if fallback_images:
    if use_selenium:
        if not check_image_url(fallback_images[0]):
            print("   Gambar pertama dari fallback gagal, mencoba Selenium...")
            selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
            if selenium_imgs:
                return selenium_imgs
            else:
                print("   Selenium tidak menghasilkan gambar, tetap pakai hasil fallback.")
    return fallback_images

# --- METODE 3: Selenium (jika masih kosong) ---
if use_selenium:
    print("   Tidak ada gambar dari metode sebelumnya, mencoba Selenium...")
    selenium_imgs = get_images_manhuaplus_with_selenium(chapter_url)
    if selenium_imgs:
        return selenium_imgs
