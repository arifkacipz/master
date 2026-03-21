#!/usr/bin/env python3
"""
Generate piano tiles patterns from MP3 files.
- Scans game/sg/ for MP3 files
- Uses librosa with better beat detection parameters
- Generates pattern JSON (easy/hard) to game/db/
- Creates playlist.json with BPM info
"""

import os
import sys
import json
import argparse
import hashlib
import numpy as np
import librosa
from pathlib import Path

# Path setup
SCRIPT_DIR = Path(__file__).parent.resolve()
MP3_DIR = SCRIPT_DIR / "sg"
DB_DIR = SCRIPT_DIR / "db"
PLAYLIST_FILE = SCRIPT_DIR / "playlist.json"

# Buat folder jika belum ada
MP3_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def estimate_bpm(y, sr):
    """Estimasi BPM lebih akurat dengan parameter yang baik."""
    # Gunakan onset strength untuk deteksi beat yang lebih presisi
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=512, tightness=100)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if tempo.size > 0 else 120.0
    else:
        tempo = float(tempo)
    return tempo, beats

def generate_pattern_from_beats(beats, bpm, is_hard=False):
    """
    beats: array waktu beat (detik)
    bpm: beats per minute
    is_hard: mode hard (tile lebih rapat dan ada tile panjang)
    """
    if len(beats) == 0:
        beat_interval = 60 / bpm
        beats = np.arange(0, 30, beat_interval)  # asumsi 30 detik

    pattern = []
    # Untuk setiap beat, buat tile
    for i, t in enumerate(beats):
        col = i % 4
        duration = 0
        if is_hard:
            # Variasi kolom untuk hard
            if i % 3 == 0:
                col = (col + 2) % 4
            if i % 7 == 0:
                col = 3 - col
            # Tile panjang (hold) pada beat tertentu
            if i % 4 == 0 and np.random.rand() < 0.3:
                duration = (60 / bpm) * 1.5  # durasi hold 1.5 beat
        pattern.append({
            "time": float(t),
            "col": col,
            "duration": duration
        })

    # Hard mode: tambahkan tile di antara beat (double time)
    if is_hard and len(beats) > 1:
        double_pattern = []
        for i in range(len(beats)-1):
            t_mid = (beats[i] + beats[i+1]) / 2
            col = (i+1) % 4
            if (i+1) % 3 == 0:
                col = (col + 1) % 4
            double_pattern.append({
                "time": float(t_mid),
                "col": col,
                "duration": 0
            })
        pattern.extend(double_pattern)
        pattern.sort(key=lambda x: x["time"])

    return pattern

def process_mp3_file(mp3_path, force=False):
    """Analyze one MP3 file, generate patterns, save JSON."""
    # ID dari nama file
    raw_name = mp3_path.stem
    clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in raw_name)
    clean = '_'.join(filter(None, clean.split('_')))
    song_id = clean[:50] if clean else f"file_{mp3_path.stem[:20]}"
    if not song_id:
        song_id = f"unknown_{hashlib.md5(mp3_path.name.encode()).hexdigest()[:8]}"

    easy_file = DB_DIR / f"{song_id}_easy.json"
    hard_file = DB_DIR / f"{song_id}_hard.json"
    if not force and easy_file.exists() and hard_file.exists():
        print(f"Pola untuk {song_id} sudah ada, lewati (gunakan --force untuk generate ulang).")
        # Tetap baca BPM dari audio untuk playlist
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
        tempo, _ = estimate_bpm(y, sr)
        return {
            "id": song_id,
            "name": raw_name,
            "url": mp3_path.name,
            "bpm": round(tempo, 2)
        }

    print(f"Menganalisis {mp3_path}")
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
    except Exception as e:
        print(f"Error loading audio {mp3_path}: {e}")
        return None

    try:
        tempo, beats = estimate_bpm(y, sr)
        # Convert beats to time in seconds
        beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
        print(f"Estimasi BPM: {tempo:.2f}, jumlah beat: {len(beat_times)}")
    except Exception as e:
        print(f"Error detecting beats for {mp3_path}: {e}")
        tempo = 120.0
        beat_times = np.array([])

    pattern_easy = generate_pattern_from_beats(beat_times, tempo, is_hard=False)
    pattern_hard = generate_pattern_from_beats(beat_times, tempo, is_hard=True)

    with open(easy_file, 'w') as f:
        json.dump(pattern_easy, f, indent=2)
    print(f"Pola easy disimpan ke {easy_file} ({len(pattern_easy)} tile)")
    with open(hard_file, 'w') as f:
        json.dump(pattern_hard, f, indent=2)
    print(f"Pola hard disimpan ke {hard_file} ({len(pattern_hard)} tile)")

    return {
        "id": song_id,
        "name": raw_name,
        "url": mp3_path.name,
        "bpm": round(tempo, 2)
    }

def save_playlist(songs_data):
    """Buat playlist.json dari data lagu yang sudah diproses."""
    playlist = []
    for song in songs_data:
        playlist.append({
            "id": song["id"],
            "name": song["name"],
            "url": song["url"],
            "bpm": song["bpm"]
        })
    playlist.sort(key=lambda x: x['name'])
    with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, indent=2, ensure_ascii=False)
    print(f"Playlist disimpan ke {PLAYLIST_FILE} ({len(playlist)} lagu)")

def main():
    parser = argparse.ArgumentParser(description="Generate piano tile patterns from MP3 files")
    parser.add_argument("--force", action="store_true", help="Force regenerate patterns for all songs")
    args = parser.parse_args()

    mp3_files = list(MP3_DIR.glob("*.mp3"))
    print(f"Ditemukan {len(mp3_files)} file MP3 di folder sg")

    songs_data = []
    for mp3_file in mp3_files:
        song_info = process_mp3_file(mp3_file, force=args.force)
        if song_info:
            songs_data.append(song_info)

    if songs_data:
        save_playlist(songs_data)
    else:
        print("Tidak ada lagu baru diproses.")

if __name__ == "__main__":
    main()
