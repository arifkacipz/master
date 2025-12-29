<?php
// URL target undangan
$url = "https://the.gandilova.com/amelda";

// Ambil isi konten dari URL tersebut
$content = file_get_contents($url);

if ($content === FALSE) {
    echo "Gagal mengambil konten. Pastikan server Anda mengaktifkan allow_url_fopen.";
    exit;
}

// TRIK PENTING:
// Karena file CSS dan Gambar di undangan biasanya menggunakan link relatif (misal: src="/style.css"),
// jika kita load mentah-mentah, tampilannya akan hancur (berantakan).
// Kita harus menyuntikkan tag <base> agar browser tahu sumber aslinya.

$baseTag = '<head><base href="https://the.gandilova.com/" />';
$content = str_replace('<head>', $baseTag, $content);

// Tampilkan hasilnya
echo $content;
?>
