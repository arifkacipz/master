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
    """Estimasi BPM dari audio. Kembalikan float."""
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # tempo bisa berupa array numpy (misal shape (1,)), kita ekstrak scalar
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if tempo.size > 0 else 120.0
    else:
        tempo = float(tempo)
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
        # Gunakan nama file tanpa ekstensi, bersihkan untuk dijadikan id
        raw_name = mp3_path.stem
        # Ganti spasi dengan underscore, hilangkan karakter non-alnum (kecuali underscore)
        clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in raw_name)
        # Hapus underscore berulang
        clean = '_'.join(filter(None, clean.split('_')))
        song_id = clean[:50] if clean else f"file_{mp3_path.stem[:20]}"
        # Jika masih kosong, beri default
        if not song_id:
            song_id = f"unknown_{hashlib.md5(mp3_path.name.encode()).hexdigest()[:8]}"

    # Check if patterns already exist and not force
    easy_file = DB_DIR / f"{song_id}_easy.json"
    hard_file = DB_DIR / f"{song_id}_hard.json"
    skip_generate = False
    if not force and easy_file.exists() and hard_file.exists():
        print(f"Pola untuk {song_id} sudah ada, lewati (gunakan --force untuk generate ulang).")
        skip_generate = True

    # Load audio
    print(f"Menganalisis {mp3_path}")
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
    except Exception as e:
        print(f"Error loading audio {mp3_path}: {e}")
        return None

    # Estimasi BPM
    try:
        bpm = estimate_bpm(y, sr)
        print(f"Estimasi BPM: {bpm:.2f}")
    except Exception as e:
        print(f"Error estimating BPM for {mp3_path}: {e}")
        bpm = 120.0  # default fallback

    # Dapatkan waktu beat
    try:
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='time')
        beat_times = beat_frames
    except Exception as e:
        print(f"Error detecting beats for {mp3_path}: {e}")
        beat_times = []

    if skip_generate:
        # Tidak perlu generate ulang, hanya return info dari file yang sudah ada
        # Kita tetap butuh bpm untuk songs.json, jadi kita gunakan bpm yang baru dihitung
        pass
    else:
        # Generate pola
        pattern_easy = generate_pattern_from_beat(beat_times, bpm, is_hard=False)
        pattern_hard = generate_pattern_from_beat(beat_times, bpm, is_hard=True)

        # Simpan ke file JSON
        with open(easy_file, 'w') as f:
            json.dump(pattern_easy, f, indent=2)
        print(f"Pola easy disimpan ke {easy_file} ({len(pattern_easy)} tile)")
        with open(hard_file, 'w') as f:
            json.dump(pattern_hard, f, indent=2)
        print(f"Pola hard disimpan ke {hard_file} ({len(pattern_hard)} tile)")

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

    processed_count = 0
    # Proses setiap file MP3
    for mp3_file in mp3_files:
        # Tentukan ID dari nama file
        raw_name = mp3_file.stem
        clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in raw_name)
        clean = '_'.join(filter(None, clean.split('_')))
        song_id = clean[:50] if clean else f"file_{mp3_file.stem[:20]}"
        if not song_id:
            song_id = f"unknown_{hashlib.md5(mp3_file.name.encode()).hexdigest()[:8]}"

        # Periksa apakah sudah ada di songs_dict dan tidak force
        if song_id in songs_dict and not args.force:
            print(f"Lagu {song_id} sudah ada di songs.json, lewati.")
            continue

        # Proses file
        try:
            song_info = process_mp3_file(mp3_file, song_id, force=args.force)
            if song_info:
                songs_dict[song_info["id"]] = song_info
                processed_count += 1
        except Exception as e:
            print(f"Error processing {mp3_file}: {e}")
            continue

    # Jika ada perubahan, simpan songs.json
    if processed_count > 0:
        save_songs(songs_dict)
        print(f"songs.json diperbarui dengan {len(songs_dict)} lagu (ditambahkan {processed_count} baru).")
    else:
        print("Tidak ada lagu baru diproses.")

if __name__ == "__main__":
    main()
