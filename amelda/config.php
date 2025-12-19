<?php
// Ambil detail koneksi dari TiDB Cloud Console (Connect -> PHP)
$host = 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com';
$port = 4000;
$user = '4Lf1oLZHxYutf7y.root';
$pass = 'dqrUuaSe4G9xINu4';
$dbname = 'test';

$conn = mysqli_init();
mysqli_ssl_set($conn, NULL, NULL, "path/to/ca-bundle.crt", NULL, NULL); // Unduh CA Bundle dari TiDB

if (!mysqli_real_connect($conn, $host, $user, $pass, $dbname, $port, NULL, MYSQLI_CLIENT_SSL)) {
    die("Koneksi Gagal: " . mysqli_connect_error());
}
?>