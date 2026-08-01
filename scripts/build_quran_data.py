#!/usr/bin/env python3
"""
ONE-TIME SETUP SCRIPT — run this once to generate quran_arabic.json.

Downloads the complete Uthmani Arabic Quran text (all 6,236 verses) from
AlQuran.cloud's bulk endpoint (sourced from Tanzil.net — the gold-standard,
manually verified Quran text used by virtually all major Quran apps).

Run this once, locally or in a throwaway GitHub Action, then commit the
resulting quran_arabic.json to your repo. After that, send_verse.py reads
the Arabic text locally — no live API call needed for Arabic ever again.

Usage:
    python build_quran_data.py

Output:
    quran_arabic.json  (~1.5 MB, all 114 surahs / 6,236 ayahs)
"""

import json
import urllib.request

URL = "https://api.alquran.cloud/v1/quran/quran-uthmani"
OUTPUT_FILE = "quran_arabic.json"


def main():
    print(f"🌐 Downloading complete Uthmani Quran text from AlQuran.cloud …")
    req = urllib.request.Request(URL, headers={"User-Agent": "QuranDailyBot-Setup/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("code") != 200:
        raise RuntimeError(f"API error: {data}")

    surahs = data["data"]["surahs"]
    print(f"✅ Downloaded {len(surahs)} surahs")

    # Build a compact lookup: { "1:1": "بِسْمِ اللَّهِ...", "1:2": "...", ... }
    quran = {}
    total_ayahs = 0
    for surah in surahs:
        surah_num = surah["number"]
        for ayah in surah["ayahs"]:
            key = f"{surah_num}:{ayah['numberInSurah']}"
            quran[key] = ayah["text"]
            total_ayahs += 1

    print(f"✅ Indexed {total_ayahs} ayahs")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(quran, f, ensure_ascii=False, indent=None, separators=(",", ":"))

    print(f"✅ Saved to {OUTPUT_FILE}")
    print(f"\nNext steps:")
    print(f"1. Commit {OUTPUT_FILE} to your GitHub repo (same folder as send_verse.py)")
    print(f"2. The updated send_verse.py will read Arabic text from this file locally")


if __name__ == "__main__":
    main()
