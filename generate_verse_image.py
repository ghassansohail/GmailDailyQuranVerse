#!/usr/bin/env python3
"""
Generates a beautifully formatted image of a Quran verse
(Arabic + English + Urdu), with the Arabic rendered large and bold
using a proper Quranic typeface, dynamically sized to fit any verse
length — from short (Al-Ikhlas) to very long (Ayat Al-Kursi and beyond).

Uses Pillow's native raqm-based text layout (direction="rtl") for
correct Arabic/Urdu shaping — no manual reshaping libraries needed.
Requires libfribidi (and ideally libharfbuzz) installed on the system;
Pillow's own wheel bundles the rest of raqm since Pillow 8.2.0.
"""

import os
from PIL import Image, ImageDraw, ImageFont, features

FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")

FONT_ARABIC   = os.path.join(FONTS_DIR, "AmiriQuran.ttf")
FONT_ENGLISH  = os.path.join(FONTS_DIR, "DejaVuSerif-Italic.ttf")
FONT_URDU     = os.path.join(FONTS_DIR, "NotoNastaliqUrdu-Regular.ttf")
FONT_HEADER   = os.path.join(FONTS_DIR, "Amiri-Bold.ttf")

CANVAS_WIDTH = 1080          # good for WhatsApp/Instagram square-ish posts
PADDING      = 70
BG_COLOR     = (250, 247, 240)      # warm off-white
TEXT_COLOR   = (30, 30, 30)
ACCENT_COLOR = (60, 110, 70)        # deep green
DIVIDER_COLOR = (210, 200, 180)

RAQM_AVAILABLE = features.check("raqm")


def rtl_kwargs() -> dict:
    """Extra kwargs to pass to draw.text()/textbbox() for RTL shaping, if available."""
    return {"direction": "rtl"} if RAQM_AVAILABLE else {}


def text_width(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, rtl: bool = False) -> int:
    kwargs = rtl_kwargs() if rtl else {}
    bbox = draw.textbbox((0, 0), text, font=font, **kwargs)
    return bbox[2] - bbox[0]


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int,
              draw: ImageDraw.Draw, rtl: bool = False) -> list[str]:
    """Wrap text at word boundaries to fit max_width. Words stay in logical
    (reading) order in the returned strings — Pillow's raqm layout handles
    correct RTL glyph direction and joining at draw time via direction='rtl'."""
    words = text.split(" ")
    lines, current = [], []

    for word in words:
        trial = current + [word]
        trial_text = " ".join(trial)
        width = text_width(draw, trial_text, font, rtl=rtl)
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_font(text: str, max_width: int, draw: ImageDraw.Draw, font_path: str,
             min_size: int, max_size: int, max_lines: int,
             rtl: bool = False) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Try decreasing font sizes until the text wraps into an acceptable
    number of lines that all fit within max_width."""
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size)
        lines = wrap_text(text, font, max_width, draw, rtl=rtl)
        if len(lines) <= max_lines:
            return font, lines
    font = ImageFont.truetype(font_path, min_size)
    lines = wrap_text(text, font, max_width, draw, rtl=rtl)
    return font, lines


def draw_line(draw: ImageDraw.Draw, xy: tuple[float, float], text: str,
              font: ImageFont.FreeTypeFont, fill, anchor: str, rtl: bool = False) -> None:
    kwargs = rtl_kwargs() if rtl else {}
    draw.text(xy, text, font=font, fill=fill, anchor=anchor, **kwargs)


def line_height(draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont, sample: str,
                 spacing_ratio: float, rtl: bool = False) -> int:
    kwargs = rtl_kwargs() if rtl else {}
    bbox = draw.textbbox((0, 0), sample, font=font, **kwargs)
    return int((bbox[3] - bbox[1]) * spacing_ratio)


def generate_verse_image(verse: dict, output_path: str) -> None:
    """
    verse: {
        'surah_number', 'ayah_number', 'surah_name_en', 'surah_name_ar',
        'arabic', 'english', 'urdu'
    }
    """
    content_width = CANVAS_WIDTH - 2 * PADDING

    probe_img = Image.new("RGB", (CANVAS_WIDTH, 100), BG_COLOR)
    probe_draw = ImageDraw.Draw(probe_img)

    header_font = ImageFont.truetype(FONT_HEADER, 34)
    label_font  = ImageFont.truetype(FONT_HEADER, 20)

    arabic_font, arabic_lines = fit_font(
        verse["arabic"], content_width, probe_draw, FONT_ARABIC,
        min_size=34, max_size=82, max_lines=10, rtl=True
    )
    english_font, english_lines = fit_font(
        verse["english"], content_width, probe_draw, FONT_ENGLISH,
        min_size=22, max_size=30, max_lines=8, rtl=False
    )
    urdu_font, urdu_lines = fit_font(
        verse["urdu"], content_width, probe_draw, FONT_URDU,
        min_size=30, max_size=42, max_lines=8, rtl=True
    )

    # ---- Compute dynamic canvas height ----
    arabic_line_h  = line_height(probe_draw, arabic_font,  "بي", 1.7, rtl=True)
    english_line_h = line_height(probe_draw, english_font, "Ay", 1.4, rtl=False)
    urdu_line_h    = line_height(probe_draw, urdu_font,    "بی", 1.8, rtl=True)

    header_h  = 60
    arabic_h  = arabic_line_h  * len(arabic_lines)
    english_h = english_line_h * len(english_lines)
    urdu_h    = urdu_line_h    * len(urdu_lines)
    label_h   = 40
    divider_h = 30
    footer_h  = 70

    total_height = (
        PADDING
        + header_h + 30
        + label_h + arabic_h + divider_h + 40
        + label_h + english_h + divider_h
        + label_h + urdu_h + divider_h
        + footer_h
        + PADDING
    )
    total_height = max(total_height, 700)

    # ---- Render final image ----
    img = Image.new("RGB", (CANVAS_WIDTH, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING

    # Header
    header_text = f"Surah {verse['surah_number']}: {verse['surah_name_en']}  ({verse['surah_name_ar']})  |  Ayah {verse['ayah_number']}"
    header_w = text_width(draw, header_text, header_font)
    draw.text(((CANVAS_WIDTH - header_w) / 2, y), header_text, font=header_font, fill=ACCENT_COLOR)
    y += header_h

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=2)
    y += 30

    # Arabic label + block (right-aligned, bold, large)
    draw_line(draw, (CANVAS_WIDTH - PADDING, y), "النص العربي", label_font, ACCENT_COLOR, "ra", rtl=True)
    y += label_h

    for line in arabic_lines:
        draw_line(draw, (CANVAS_WIDTH - PADDING, y), line, arabic_font, TEXT_COLOR, "ra", rtl=True)
        y += arabic_line_h
    y += divider_h + 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    y += 30

    # English label + block (left-aligned, italic)
    draw.text((PADDING, y), "English — Sahih International", font=label_font, fill=ACCENT_COLOR)
    y += label_h
    for line in english_lines:
        draw.text((PADDING, y), line, font=english_font, fill=TEXT_COLOR)
        y += english_line_h
    y += divider_h - 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    y += 20

    # Urdu label + block (right-aligned)
    draw_line(draw, (CANVAS_WIDTH - PADDING, y), "اردو ترجمہ — فتح محمد جالندھری", label_font, ACCENT_COLOR, "ra", rtl=True)
    y += label_h
    for line in urdu_lines:
        draw_line(draw, (CANVAS_WIDTH - PADDING, y), line, urdu_font, TEXT_COLOR, "ra", rtl=True)
        y += urdu_line_h
    y += divider_h - 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=2)
    y += 25

    # Footer
    footer_font = ImageFont.truetype(FONT_ENGLISH, 22)
    footer_text = "May Allah guide us all. آمین"
    footer_w = text_width(draw, footer_text, footer_font)
    draw.text(((CANVAS_WIDTH - footer_w) / 2, y), footer_text, font=footer_font, fill=(120, 120, 120))

    img.save(output_path, "PNG")
    print(f"✅ Image saved: {output_path} ({CANVAS_WIDTH}x{total_height}) — raqm: {RAQM_AVAILABLE}")


if __name__ == "__main__":
    test_verse_short = {
        "surah_number": 112, "ayah_number": 1,
        "surah_name_en": "Al-Ikhlaas", "surah_name_ar": "الإخلاص",
        "arabic": "قُلْ هُوَ اللَّهُ أَحَدٌ",
        "english": "Say, He is Allah, who is One,",
        "urdu": "کہہ دو وہ اللہ ایک ہے",
    }

    test_verse_long = {
        "surah_number": 2, "ayah_number": 282,
        "surah_name_en": "Al-Baqarah", "surah_name_ar": "البقرة",
        "arabic": (
            "يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا تَدَايَنتُم بِدَيْنٍ إِلَىٰ أَجَلٍ مُّسَمًّى فَاكْتُبُوهُ "
            "وَلْيَكْتُب بَّيْنَكُمْ كَاتِبٌ بِالْعَدْلِ ۚ وَلَا يَأْبَ كَاتِبٌ أَن يَكْتُبَ كَمَا عَلَّمَهُ اللَّهُ "
            "فَلْيَكْتُبْ وَلْيُمْلِلِ الَّذِي عَلَيْهِ الْحَقُّ وَلْيَتَّقِ اللَّهَ رَبَّهُ وَلَا يَبْخَسْ مِنْهُ شَيْئًا"
        ),
        "english": (
            "O you who have believed, when you contract a debt for a specified term, write it down. "
            "And let a scribe write [it] between you in justice. Let no scribe refuse to write as Allah "
            "has taught him. So let him write and let the one who has the obligation dictate."
        ),
        "urdu": (
            "اے ایمان والو جب تم ایک دوسرے سے ایک مقررہ مدت کے لیے قرض کا معاملہ کرو تو اسے لکھ لیا کرو "
            "اور چاہیے کہ تمہارے درمیان کوئی لکھنے والا انصاف کے ساتھ لکھے اور کاتب کو یہ زیبا نہیں کہ جیسا "
            "اللہ نے اسے سکھایا ہے وہ لکھنے سے انکار کرے پس اسے لکھنا چاہیے"
        ),
    }

    os.makedirs("/tmp/verse_images", exist_ok=True)
    generate_verse_image(test_verse_short, "/tmp/verse_images/short.png")
    generate_verse_image(test_verse_long, "/tmp/verse_images/long.png")

