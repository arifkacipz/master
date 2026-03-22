#!/usr/bin/env python3
"""
Generate piano tile patterns from MP3 files with high precision beat detection.
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

MP3_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

def get_beat_times(y, sr):
    """
    Deteksi beat yang akurat.
    Returns: (tempo, beat_times_in_seconds)
    """
    hop_length = 512
    # Onset strength untuk deteksi yang lebih presisi
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    # Beat track dengan tightness tinggi
    tempo, beats = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        tightness=100
    )
    # Konversi frame ke waktu
    beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=hop_length)
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo[0]) if tempo.size > 0 else 120.0
    else:
        tempo = float(tempo)
    return tempo, beat_times

def generate_pattern(beat_times, bpm, is_hard=False):
    """Generate tile pattern based on beat times."""
    pattern = []
    for i, t in enumerate(beat_times):
        col = i % 4
        duration = 0
        if is_hard:
            # Variasi kolom untuk mode hard
            if i % 3 == 0:
                col = (col + 2) % 4
            if i % 7 == 0:
                col = 3 - col
            # Tile panjang pada beat tertentu (hold)
            if i % 4 == 0 and np.random.rand() < 0.3:
                duration = (60 / bpm) * 1.5
        pattern.append({"time": float(t), "col": col, "duration": duration})

    # Mode hard: tambahkan tile di antara beat (double time)
    if is_hard and len(beat_times) > 1:
        double = []
        for i in range(len(beat_times)-1):
            t_mid = (beat_times[i] + beat_times[i+1]) / 2
            col = (i+1) % 4
            if (i+1) % 3 == 0:
                col = (col + 1) % 4
            double.append({"time": float(t_mid), "col": col, "duration": 0})
        pattern.extend(double)
        pattern.sort(key=lambda x: x["time"])
    return pattern

def process_mp3(mp3_path, force):
    raw_name = mp3_path.stem
    clean = ''.join(c if c.isalnum() or c == '_' else '_' for c in raw_name)
    clean = '_'.join(filter(None, clean.split('_')))
    song_id = clean[:50] if clean else f"file_{mp3_path.stem[:20]}"
    if not song_id:
        song_id = f"unknown_{hashlib.md5(mp3_path.name.encode()).hexdigest()[:8]}"

    easy_file = DB_DIR / f"{song_id}_easy.json"
    hard_file = DB_DIR / f"{song_id}_hard.json"
    if not force and easy_file.exists() and hard_file.exists():
        # Skip generate, tapi tetap baca BPM untuk playlist
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
        tempo, _ = get_beat_times(y, sr)
        return {"id": song_id, "name": raw_name, "url": mp3_path.name, "bpm": round(tempo, 2)}

    print(f"Processing: {mp3_path}")
    y, sr = librosa.load(mp3_path, sr=None, mono=True)
    tempo, beat_times = get_beat_times(y, sr)
    print(f"BPM: {tempo:.2f}, Beats detected: {len(beat_times)}")

    pattern_easy = generate_pattern(beat_times, tempo, False)
    pattern_hard = generate_pattern(beat_times, tempo, True)

    with open(easy_file, 'w') as f:
        json.dump(pattern_easy, f, indent=2)
    with open(hard_file, 'w') as f:
        json.dump(pattern_hard, f, indent=2)

    print(f"Saved easy ({len(pattern_easy)} tiles) and hard ({len(pattern_hard)} tiles)")
    return {"id": song_id, "name": raw_name, "url": mp3_path.name, "bpm": round(tempo, 2)}

def main():
    parser = argparse.ArgumentParser(description="Generate piano tile patterns")
    parser.add_argument("--force", action="store_true", help="Regenerate all patterns")
    args = parser.parse_args()

    mp3_files = list(MP3_DIR.glob("*.mp3"))
    print(f"Found {len(mp3_files)} MP3 files")

    songs = []
    for mp3 in mp3_files:
        info = process_mp3(mp3, args.force)
        if info:
            songs.append(info)

    if songs:
        with open(PLAYLIST_FILE, 'w') as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
        print(f"Playlist saved to {PLAYLIST_FILE}")

if __name__ == "__main__":
    main()
