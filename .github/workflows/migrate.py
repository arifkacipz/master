name: Bulk File Migration

on:
  workflow_dispatch: # Memungkinkan kamu menjalankan script secara manual melalui UI GitHub

jobs:
  migrate:
    runs-on: ubuntu-latest
    permissions:
      contents: write # Wajib agar bot bisa melakukan commit & push

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Run Migration Script
        run: python migrate.py

      - name: Commit and Push Changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add .
          
          # Cek apakah ada perubahan sebelum melakukan commit
          if git diff --staged --quiet; then
            echo "Tidak ada perubahan yang perlu di-commit."
          else
            git commit -m "chore: reorganize db subfolders via github actions"
            git push
          fi
