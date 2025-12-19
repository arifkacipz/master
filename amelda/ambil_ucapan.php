<?php
include 'config.php';

$result = mysqli_query($conn, "SELECT nama, kehadiran, ucapan FROM rsvp_ucapan ORDER BY id DESC");
$rows = [];

while($r = mysqli_fetch_assoc($result)) {
    $rows[] = $r;
}

header('Content-Type: application/json');
echo json_encode($rows);
?>