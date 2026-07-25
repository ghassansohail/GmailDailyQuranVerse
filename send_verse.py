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

CDN_BASE = "https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions"

# Edition identifiers on fawazahmed0/quran-api
EDITION_ARABIC  = "ara-quranuthmani"
EDITION_ENGLISH = "eng-sahih"
EDITION_URDU    = "urd-jalandhry"

# Surah English/Arabic display names (index 0 unused, 1-114 = surah number)
SURAH_NAMES_EN = [
    "", "Al-Faatiha","Al-Baqarah","Aal-i-Imraan","An-Nisaa","Al-Maaida","Al-An'aam","Al-A'raaf",
    "Al-Anfaal","At-Tawba","Yunus","Hud","Yusuf","Ar-Ra'd","Ibrahim","Al-Hijr","An-Nahl",
    "Al-Israa","Al-Kahf","Maryam","Taa-Haa","Al-Anbiyaa","Al-Hajj","Al-Muminoon","An-Noor",
    "Al-Furqaan","Ash-Shu'araa","An-Naml","Al-Qasas","Al-Ankaboot","Ar-Room","Luqman","As-Sajda",
    "Al-Ahzaab","Saba","Faatir","Yaseen","As-Saaffaat","Saad","Az-Zumar","Al-Ghaafir",
    "Fussilat","Ash-Shura","Az-Zukhruf","Ad-Dukhaan","Al-Jaathiya","Al-Ahqaf","Muhammad","Al-Fath",
    "Al-Hujuraat","Qaaf","Adh-Dhaariyat","At-Tur","An-Najm","Al-Qamar","Ar-Rahmaan","Al-Waaqia",
    "Al-Hadid","Al-Mujaadila","Al-Hashr","Al-Mumtahana","As-Saff","Al-Jumu'a","Al-Munaafiqoon",
    "At-Taghaabun","At-Talaaq","At-Tahrim","Al-Mulk","Al-Qalam","Al-Haaqqa","Al-Ma'aarij","Nooh",
    "Al-Jinn","Al-Muzzammil","Al-Muddaththir","Al-Qiyaama","Al-Insaan","Al-Mursalaat","An-Naba",
    "An-Naazi'aat","Abasa","At-Takwir","Al-Infitaar","Al-Mutaffifin","Al-Inshiqaaq","Al-Burooj",
    "At-Taariq","Al-A'laa","Al-Ghaashiya","Al-Fajr","Al-Balad","Ash-Shams","Al-Lail","Ad-Dhuhaa",
    "Ash-Sharh","At-Tin","Al-Alaq","Al-Qadr","Al-Bayyina","Az-Zalzala","Al-Aadiyaat","Al-Qaari'a",
    "At-Takaathur","Al-Asr","Al-Humaza","Al-Fil","Quraish","Al-Maa'un","Al-Kawthar","Al-Kaafiroon",
    "An-Nasr","Al-Masad","Al-Ikhlaas","Al-Falaq","An-Naas",
]
SURAH_NAMES_AR = [
    "", "الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة",
    "يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه",
    "الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم",
    "لقمان","السجدة","الأحزاب","سبإ","فاطر","يس","الصافات","ص","الزمر","غافر","فصلت","الشورى",
    "الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق","الذاريات","الطور","النجم",
    "القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون",
    "التغابن","الطلاق","التحريم","الملك","القلم","الحاقة","المعارج","نوح","الجن","المزمل","المدثر",
    "القيامة","الإنسان","المرسلات","النبأ","النازعات","عبس","التكوير","الإنفطار","المطففين",
    "الإنشقاق","البروج","الطارق","الأعلى","الغاشية","الفجر","البلد","الشمس","الليل","الضحى",
    "الشرح","التين","العلق","القدر","البينة","الزلزلة","العاديات","القارعة","التكاثر","العصر",
    "الهمزة","الفيل","قريش","الماعون","الكوثر","الكافرون","النصر","المسد","الإخلاص","الفلق","الناس",
]


def get_verse(surah: int, ayah: int) -> dict:
    print(f"🌐 Fetching {surah}:{ayah} from Quran API (jsDelivr CDN) …")

    arabic  = _fetch_single(EDITION_ARABIC,  surah, ayah)
    english = _fetch_single(EDITION_ENGLISH, surah, ayah)
    urdu    = _fetch_single(EDITION_URDU,    surah, ayah)

    return {
        "surah_number":  surah,
        "ayah_number":   ayah,
        "surah_name_en": SURAH_NAMES_EN[surah],
        "surah_name_ar": SURAH_NAMES_AR[surah],
        "arabic":        arabic,
        "english":       english,
        "urdu":          urdu,
    }


def _fetch_single(edition: str, surah: int, ayah: int) -> str:
    url = f"{CDN_BASE}/{edition}/{surah}/{ayah}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "QuranDailyBot/4.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["text"]


# ── Email builder ─────────────────────────────────────────────────────────────

def build_email(v: dict) -> MIMEMultipart:
    subject = f"🌙 Quran Daily — Surah {v['surah_number']} ({v['surah_name_en']}), Ayah {v['ayah_number']}"

    whatsapp = (
        f"🌙 *Quran — Daily Verse*\n"
        f"📖 *Surah {v['surah_number']}: {v['surah_name_en']}* ({v['surah_name_ar']}) | *Ayah {v['ayah_number']}*\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"🔤 *Arabic:*\n{v['arabic']}\n\n"
        f"🇬🇧 *English:*\n_{v['english']}_\n\n"
        f"🇵🇰 *Urdu:*\n{v['urdu']}\n\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"_May Allah guide us all. آمین_"
    )

    instagram = (
        f"🌙 Quran — Daily Verse\n"
        f"📖 Surah {v['surah_number']}: {v['surah_name_en']} ({v['surah_name_ar']}) | Ayah {v['ayah_number']}\n\n"
        f"🔤 Arabic:\n{v['arabic']}\n\n"
        f"🇬🇧 English:\n{v['english']}\n\n"
        f"🇵🇰 Urdu:\n{v['urdu']}\n\n"
        f"May Allah guide us all. آمین\n\n"
        f"#Quran #Islam #DailyQuran #QuranVerse #IslamicReminder #Alhamdulillah"
    )

    body = (
        f"— WHATSAPP —\n\n{whatsapp}\n\n\n"
        f"{'═' * 40}\n\n"
        f"— INSTAGRAM —\n\n{instagram}"
    )

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"]    = f"Quran Daily <{GMAIL_ADDRESS}>"
    msg["To"]      = GMAIL_ADDRESS
    msg.attach(MIMEText(body, "plain", "utf-8"))
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
