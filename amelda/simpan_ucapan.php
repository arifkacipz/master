<?php
include 'config.php';

$nama = mysqli_real_escape_string($conn, $_POST['nama']);
$kehadiran = mysqli_real_escape_string($conn, $_POST['kehadiran']);
$ucapan = mysqli_real_escape_string($conn, $_POST['ucapan']);

$query = "INSERT INTO rsvp_ucapan (nama, kehadiran, ucapan) VALUES ('$nama', '$kehadiran', '$ucapan')";

if (mysqli_query($conn, $query)) {
    echo json_encode(['status' => 'success']);
} else {
    echo json_encode(['status' => 'error']);
}
?>