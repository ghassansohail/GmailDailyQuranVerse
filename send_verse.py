#!/usr/bin/env python3
"""
Quran Daily Verse — Gmail Sender
Sends one verse per day (Arabic + English + Urdu) to your Gmail address.
Verses go in order: Al-Fatihah 1:1 → An-Nas 114:6, then loop.
State is persisted in state.json, committed back to repo by GitHub Actions.

Required GitHub Secrets:
  GMAIL_ADDRESS   — your Gmail address (sender + recipient)
  GMAIL_APP_PASSWORD — 16-character app password from Google account settings
"""

import json
import os
import sys
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Quran metadata: (surah_number, total_ayahs) ──────────────────────────────
SURAHS = [
    (1,7),(2,286),(3,200),(4,176),(5,120),(6,165),(7,206),(8,75),(9,129),(10,109),
    (11,123),(12,111),(13,43),(14,52),(15,99),(16,128),(17,111),(18,110),(19,98),(20,135),
    (21,112),(22,78),(23,118),(24,64),(25,77),(26,227),(27,93),(28,88),(29,69),(30,60),
    (31,34),(32,30),(33,73),(34,54),(35,45),(36,83),(37,182),(38,88),(39,75),(40,85),
    (41,54),(42,53),(43,89),(44,59),(45,37),(46,35),(47,38),(48,29),(49,18),(50,45),
    (51,60),(52,49),(53,62),(54,55),(55,78),(56,96),(57,29),(58,22),(59,24),(60,13),
    (61,14),(62,11),(63,11),(64,18),(65,12),(66,12),(67,30),(68,52),(69,52),(70,44),
    (71,28),(72,28),(73,20),(74,56),(75,40),(76,31),(77,50),(78,40),(79,46),(80,42),
    (81,29),(82,19),(83,36),(84,25),(85,22),(86,17),(87,19),(88,26),(89,30),(90,20),
    (91,15),(92,21),(93,11),(94,8),(95,8),(96,19),(97,5),(98,8),(99,8),(100,11),
    (101,11),(102,8),(103,3),(104,9),(105,5),(106,4),(107,7),(108,3),(109,6),(110,3),
    (111,5),(112,4),(113,5),(114,6),
]

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"surah": 1, "ayah": 1}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"✅ State saved → Surah {state['surah']}, Ayah {state['ayah']}")


def next_verse(surah: int, ayah: int) -> tuple[int, int]:
    _, total = SURAHS[surah - 1]
    if ayah < total:
        return surah, ayah + 1
    elif surah < 114:
        return surah + 1, 1
    else:
        return 1, 1


# ── Quran API ─────────────────────────────────────────────────────────────────

def get_verse(surah: int, ayah: int) -> dict:
    editions = "quran-uthmani,en.sahih,ur.jalandhry"
    url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/editions/{editions}"
    print(f"🌐 Fetching {surah}:{ayah} from AlQuran.cloud …")
    req = urllib.request.Request(url, headers={"User-Agent": "QuranDailyBot/3.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("code") != 200:
        raise RuntimeError(f"AlQuran API error: {data}")
    results = data["data"]
    return {
        "surah_number":  surah,
        "ayah_number":   ayah,
        "surah_name_en": results[0]["surah"]["englishName"],
        "surah_name_ar": results[0]["surah"]["name"],
        "arabic":        results[0]["text"],
        "english":       results[1]["text"],
        "urdu":          results[2]["text"],
    }


# ── Email builder ─────────────────────────────────────────────────────────────

def build_email(v: dict) -> MIMEMultipart:
    subject = f"🌙 Quran Daily — Surah {v['surah_number']} ({v['surah_name_en']}), Ayah {v['ayah_number']}"

    html = f"""
<html><body style="font-family: Georgia, serif; max-width: 600px; margin: 40px auto; color: #222; line-height: 1.8;">
  <h2 style="color: #2e7d32; border-bottom: 1px solid #c8e6c9; padding-bottom: 8px;">
    🌙 Quran — Daily Verse
  </h2>
  <p style="color: #555; font-size: 14px;">
    <strong>Surah {v['surah_number']}: {v['surah_name_en']}</strong>
    &nbsp;({v['surah_name_ar']})&nbsp;|&nbsp;Ayah {v['ayah_number']}
  </p>

  <table width="100%" style="border-top: 1px solid #eee; margin-top: 16px;">

    <tr><td style="padding: 16px 0 4px;">
      <span style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Arabic</span>
    </td></tr>
    <tr><td>
      <p style="font-size: 26px; text-align: right; direction: rtl; font-family: 'Traditional Arabic', serif; color: #1a1a1a; line-height: 2;">
        {v['arabic']}
      </p>
    </td></tr>

    <tr><td style="padding: 16px 0 4px; border-top: 1px solid #eee;">
      <span style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">English — Sahih International</span>
    </td></tr>
    <tr><td>
      <p style="font-size: 16px; color: #333; font-style: italic;">
        {v['english']}
      </p>
    </td></tr>

    <tr><td style="padding: 16px 0 4px; border-top: 1px solid #eee;">
      <span style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px;">Urdu — Fateh Muhammad Jalandhry</span>
    </td></tr>
    <tr><td>
      <p style="font-size: 18px; text-align: right; direction: rtl; font-family: 'Noto Nastaliq Urdu', serif; color: #1a1a1a; line-height: 2.2;">
        {v['urdu']}
      </p>
    </td></tr>

  </table>

  <p style="margin-top: 32px; font-size: 12px; color: #aaa; border-top: 1px solid #eee; padding-top: 12px;">
    May Allah guide us all. آمین
  </p>
</body></html>
"""

    plain = (
        f"Quran — Daily Verse\n"
        f"Surah {v['surah_number']}: {v['surah_name_en']} ({v['surah_name_ar']}) | Ayah {v['ayah_number']}\n"
        f"{'─' * 40}\n\n"
        f"Arabic:\n{v['arabic']}\n\n"
        f"English:\n{v['english']}\n\n"
        f"Urdu:\n{v['urdu']}\n\n"
        f"May Allah guide us all. آمین"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Quran Daily <{GMAIL_ADDRESS}>"
    msg["To"]      = GMAIL_ADDRESS
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    return msg


# ── Gmail sender ──────────────────────────────────────────────────────────────

def send_email(msg: MIMEMultipart) -> None:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("⚠️  GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping send.")
        return

    print(f"📨 Sending email to {GMAIL_ADDRESS} …")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())
    print("✅ Email sent!")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    state = load_state()
    surah, ayah = state["surah"], state["ayah"]
    print(f"📌 Today's verse: Surah {surah}, Ayah {ayah}")

    verse = get_verse(surah, ayah)
    msg   = build_email(verse)
    send_email(msg)

    next_s, next_a = next_verse(surah, ayah)
    save_state({"surah": next_s, "ayah": next_a})


if __name__ == "__main__":
    main()
