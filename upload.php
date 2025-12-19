<?php
if (isset($_POST['submit'])) {
    $targetDir = "asn/";
    $maxSize = 500 * 1024; // 512.000 Bytes

    // Membuat folder 'asn' jika belum ada
    if (!file_exists($targetDir)) {
        mkdir($targetDir, 0777, true);
    }

    $fileName = basename($_FILES["fileTxt"]["name"]);
    $fileSize = $_FILES["fileTxt"]["size"];
    $targetFilePath = $targetDir . $fileName;
    $fileType = strtolower(pathinfo($targetFilePath, PATHINFO_EXTENSION));

    // 1. Validasi Ekstensi
    if ($fileType != "txt") {
        echo "Gagal: Hanya file .txt yang diizinkan.";
    } 
    // 2. Validasi Ukuran File (500KB)
    elseif ($fileSize > $maxSize) {
        echo "Gagal: Ukuran file terlalu besar! Maksimal adalah 500 KB.";
    } 
    // 3. Proses Upload
    else {
        if (move_uploaded_file($_FILES["fileTxt"]["tmp_name"], $targetFilePath)) {
            echo "Berhasil! File <b>" . $fileName . "</b> terunggah ke folder asn.";
        } else {
            echo "Maaf, terjadi kesalahan teknis saat proses simpan.";
        }
    }
}
?>