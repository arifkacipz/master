#!/usr/bin/env python3
"""
Generate piano tiles patterns from MP3 files.
- Scans game/sg/ for MP3 files (both downloaded and manually uploaded)
- Reads existing songs.json (if exists)
- Processes each new MP3: analyze beat, generate pattern JSON (easy/hard) to game/db/
- Updates songs.json with new song entries
- Also processes songs listed in songs.json (if they have missing patterns)

Usage:
    python ptn.py [--force]   # force regenerate patterns for all songs
"""

import os
import sys
import json
import argparse
import numpy as np
import librosa
import requests
import hashlib
from pathlib import Path

# Path setup
SCRIPT_DIR = Path(__file__).parent.resolve()
MP3_DIR = SCRIPT_DIR / "sg"
DB_DIR = SCRIPT_DIR / "db"
SONGS_FILE = SCRIPT_DIR / "songs.json"

# Buat folder jika belum ada
MP3_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def load_songs():
    """Load existing songs.json, return dict of songs by id."""
    if SONGS_FILE.exists():
        with open(SONGS_FILE, 'r') as f:
            songs = json.load(f)
        return {s['id']: s for s in songs}
    return {}

def save_songs(songs_dict):
    """Save songs dict to songs.json."""
    songs_list = list(songs_dict.values())
    with open(SONGS_FILE, 'w') as f:
        json.dump(songs_list, f, indent=2, ensure_ascii=False)

def estimate_bpm(y, sr):
    """Estimasi BPM dari audio."""
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return tempo

def generate_pattern_from_beat(beat_times, bpm, is_hard=False):
    """
    beat_times: array waktu beat (detik) dari librosa
    bpm: beats per minute
    is_hard: mode hard (tile lebih rapat dan ada tile panjang)
    """
    if len(beat_times) == 0:
        # fallback: buat berdasarkan BPM
        beat_interval = 60 / bpm
        beat_times = np.arange(0, 30, beat_interval)  # asumsi 30 detik
    else:
        beat_times = beat_times.tolist()

    pattern = []
    # Untuk setiap beat, buat tile
    for i, t in enumerate(beat_times):
        col = i % 4
        duration = 0
        if is_hard:
            # Variasi kolom
            if i % 3 == 0:
                col = (col + 2) % 4
            if i % 7 == 0:
                col = 3 - col
            # Tile panjang pada beat tertentu (durasi 1.5 beat)
            if i % 4 == 0 and np.random.rand() < 0.3:
                duration = (60 / bpm) * 1.5
        pattern.append({
            "time": t,
            "col": col,
            "duration": duration
        })

    # Hard mode: tambahkan tile di antara beat (double time)
    if is_hard and len(beat_times) > 1:
        double_pattern = []
        for i in range(len(beat_times)-1):
            t_mid = (beat_times[i] + beat_times[i+1]) / 2
            col = (i+1) % 4
            if (i+1) % 3 == 0:
                col = (col + 1) % 4
            double_pattern.append({
                "time": t_mid,
                "col": col,
                "duration": 0
            })
        pattern.extend(double_pattern)
        pattern.sort(key=lambda x: x["time"])

    return pattern

def process_mp3_file(mp3_path, song_id=None, force=False):
    """
    Analyze one MP3 file, generate patterns, save JSON.
    Returns dict with song info: id, name, bpm.
    """
    # Generate id from filename if not provided
    if song_id is None:
        song_id = mp3_path.stem.replace(' ', '_').lower()
        # Bersihkan karakter yang tidak valid
        song_id = ''.join(c for c in song_id if c.isalnum() or c == '_')
        # Batasi panjang
        song_id = song_id[:50]

    # Check if patterns already exist and not force
    easy_file = DB_DIR / f"{song_id}_easy.json"
    hard_file = DB_DIR / f"{song_id}_hard.json"
    if not force and easy_file.exists() and hard_file.exists():
        print(f"Pola untuk {song_id} sudah ada, lewati (gunakan --force untuk generate ulang).")
        # Baca bpm dari file JSON? Lebih baik simpan bpm di metadata.
        # Kita akan membaca bpm dari pola (tidak ada bpm di pola). Kita bisa return dummy.
        # Untuk update songs.json, kita perlu bpm. Bisa baca dari file pola atau generate ulang.
        # Kita asumsikan bpm tidak tersimpan, jadi kita generate ulang untuk mendapatkan bpm.
        # Atau kita bisa menyimpan bpm di file metadata terpisah, tapi untuk sederhana kita generate ulang.
        # Untuk efisiensi, jika force=False, kita hanya skip generate tapi tetap return info dari file yang ada?
        # Tapi songs.json perlu bpm, jadi kita tetap perlu load audio.
        # Kita proses ulang tapi skip save pattern.
        pass  # kita tetap lanjut untuk menghitung bpm, tapi skip save pattern.

    # Load audio
    print(f"Menganalisis {mp3_path}")
    y, sr = librosa.load(mp3_path, sr=None, mono=True)

    # Estimasi BPM
    bpm = estimate_bpm(y, sr)
    print(f"Estimasi BPM: {bpm:.2f}")

    # Dapatkan waktu beat
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='time')
    beat_times = beat_frames

    # Generate pola
    pattern_easy = generate_pattern_from_beat(beat_times, bpm, is_hard=False)
    pattern_hard = generate_pattern_from_beat(beat_times, bpm, is_hard=True)

    # Simpan ke file JSON (hanya jika force atau file belum ada)
    if force or not easy_file.exists():
        with open(easy_file, 'w') as f:
            json.dump(pattern_easy, f, indent=2)
        print(f"Pola easy disimpan ke {easy_file}")
    if force or not hard_file.exists():
        with open(hard_file, 'w') as f:
            json.dump(pattern_hard, f, indent=2)
        print(f"Pola hard disimpan ke {hard_file}")

    return {
        "id": song_id,
        "name": mp3_path.stem,
        "url": mp3_path.name,   # relative path atau nama file saja
        "bpm": round(bpm, 2)
    }

def main():
    parser = argparse.ArgumentParser(description="Generate piano tile patterns from MP3 files")
    parser.add_argument("--force", action="store_true", help="Force regenerate patterns for all songs")
    args = parser.parse_args()

    # Muat daftar lagu yang sudah ada
    songs_dict = load_songs()

    # Cari semua file MP3 di folder sg
    mp3_files = list(MP3_DIR.glob("*.mp3"))
    print(f"Ditemukan {len(mp3_files)} file MP3 di folder sg")

    # Proses setiap file MP3
    for mp3_file in mp3_files:
        # Tentukan ID dari nama file
        # Nama file dijadikan id, misal "song1.mp3" -> id "song1"
        song_id = mp3_file.stem.replace(' ', '_').lower()
        song_id = ''.join(c for c in song_id if c.isalnum() or c == '_')
        # Periksa apakah sudah ada di songs_dict
        if song_id in songs_dict and not args.force:
            print(f"Lagu {song_id} sudah ada di songs.json, lewati.")
            continue

        # Proses file
        song_info = process_mp3_file(mp3_file, song_id, force=args.force)

        # Tambahkan ke songs_dict
        songs_dict[song_id] = song_info

    # Jika ada perubahan, simpan songs.json
    if songs_dict:
        save_songs(songs_dict)
        print(f"songs.json diperbarui dengan {len(songs_dict)} lagu.")
    else:
        print("Tidak ada lagu baru diproses.")

if __name__ == "__main__":
    main()
