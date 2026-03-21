#!/usr/bin/env python3
"""
Generate piano tiles patterns from MP3 files.
- Download MP3 from URLs in songs.json to ../game/sg/
- Analyze beat using librosa
- Generate pattern JSON for easy and hard modes
- Save JSON to ../game/db/
"""

import os
import json
import requests
import numpy as np
import librosa
import sys
from pathlib import Path

# Konfigurasi path (relatif terhadap lokasi script)
BASE_DIR = Path(__file__).parent.parent  # ke repo root
SONGS_CONFIG = BASE_DIR / "songs.json"
MP3_DIR = BASE_DIR / "game" / "sg"
DB_DIR = BASE_DIR / "game" / "db"

# Buat folder jika belum ada
MP3_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def download_mp3(url, filename):
    """Unduh MP3 dari URL ke folder sg"""
    filepath = MP3_DIR / filename
    if filepath.exists():
        print(f"File {filename} sudah ada, lewati download")
        return filepath
    print(f"Mengunduh {url} -> {filepath}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return filepath

def estimate_bpm(y, sr):
    """Estimasi BPM dari audio"""
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

def process_song(song_info):
    """Proses satu lagu: download, analisis beat, generate pola, simpan JSON"""
    song_id = song_info["id"]
    name = song_info["name"]
    url = song_info["url"]
    bpm = song_info.get("bpm")

    # Download MP3
    mp3_filename = f"{song_id}.mp3"
    mp3_path = download_mp3(url, mp3_filename)

    # Load audio
    print(f"Menganalisis {mp3_path}")
    y, sr = librosa.load(mp3_path, sr=None, mono=True)

    # Estimasi BPM jika tidak disediakan
    if bpm is None:
        bpm = estimate_bpm(y, sr)
        print(f"Estimasi BPM untuk {song_id}: {bpm:.2f}")

    # Dapatkan waktu beat
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='time')
    beat_times = beat_frames

    # Generate pola
    pattern_easy = generate_pattern_from_beat(beat_times, bpm, is_hard=False)
    pattern_hard = generate_pattern_from_beat(beat_times, bpm, is_hard=True)

    # Simpan ke file JSON
    easy_file = DB_DIR / f"{song_id}_easy.json"
    hard_file = DB_DIR / f"{song_id}_hard.json"

    with open(easy_file, 'w') as f:
        json.dump(pattern_easy, f, indent=2)
    with open(hard_file, 'w') as f:
        json.dump(pattern_hard, f, indent=2)

    print(f"Pola untuk {song_id} (easy: {len(pattern_easy)} tile, hard: {len(pattern_hard)} tile) disimpan.")
    return True

def main():
    if not SONGS_CONFIG.exists():
        print(f"File konfigurasi {SONGS_CONFIG} tidak ditemukan!")
        sys.exit(1)

    with open(SONGS_CONFIG, 'r') as f:
        songs = json.load(f)

    for song in songs:
        try:
            process_song(song)
        except Exception as e:
            print(f"Gagal memproses {song.get('id', 'unknown')}: {e}")

if __name__ == "__main__":
    main()
