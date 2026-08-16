#!/usr/bin/env python3
"""
Generates a beautifully formatted image of a Quran verse
(Arabic + English + Urdu), with the Arabic rendered large and bold
using a proper Quranic typeface, dynamically sized to fit any verse
length — from short (Al-Ikhlas) to very long (Ayat Al-Kursi and beyond).
"""

import os
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

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


def shape_arabic(text: str) -> str:
    """Reshape Arabic text so letters join correctly, then fix bidi order."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def wrap_text_rtl(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    """
    Wrap already-shaped RTL text at word boundaries to fit max_width.
    Words are split on the ORIGINAL text before shaping — so we shape
    per-line after splitting, since reshape() must run on full logical text.
    """
    words = text.split(" ")
    lines, current = [], []

    for word in words:
        trial = current + [word]
        trial_text = shape_arabic(" ".join(trial))
        bbox = draw.textbbox((0, 0), trial_text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def wrap_text_ltr(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    words = text.split(" ")
    lines, current = [], []
    for word in words:
        trial = current + [word]
        trial_text = " ".join(trial)
        bbox = draw.textbbox((0, 0), trial_text, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_arabic_font(text: str, max_width: int, draw: ImageDraw.Draw,
                     min_size: int = 34, max_size: int = 82,
                     max_lines: int = 10) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """
    Try decreasing font sizes until the Arabic verse wraps into a
    reasonable number of lines that all fit within max_width.
    Returns the chosen font and the wrapped (shaped, bidi-ordered) lines.
    """
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(FONT_ARABIC, size)
        lines = wrap_text_rtl(text, font, max_width, draw)
        if len(lines) <= max_lines:
            shaped_lines = [shape_arabic(line) for line in lines]
            return font, shaped_lines
    # Fallback: use min size regardless of line count
    font = ImageFont.truetype(FONT_ARABIC, min_size)
    lines = wrap_text_rtl(text, font, max_width, draw)
    shaped_lines = [shape_arabic(line) for line in lines]
    return font, shaped_lines


def fit_wrapped_font(text: str, max_width: int, draw: ImageDraw.Draw, font_path: str,
                      min_size: int = 24, max_size: int = 40,
                      max_lines: int = 12, rtl: bool = False) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    wrap_fn = wrap_text_rtl if rtl else wrap_text_ltr
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size)
        lines = wrap_fn(text, font, max_width, draw)
        if len(lines) <= max_lines:
            if rtl:
                lines = [shape_arabic(l) for l in lines]
            return font, lines
    font = ImageFont.truetype(font_path, min_size)
    lines = wrap_fn(text, font, max_width, draw)
    if rtl:
        lines = [shape_arabic(l) for l in lines]
    return font, lines


def generate_verse_image(verse: dict, output_path: str) -> None:
    """
    verse: {
        'surah_number', 'ayah_number', 'surah_name_en', 'surah_name_ar',
        'arabic', 'english', 'urdu'
    }
    """
    content_width = CANVAS_WIDTH - 2 * PADDING

    # Use a throwaway image/draw context for measuring during the fit passes
    probe_img = Image.new("RGB", (CANVAS_WIDTH, 100), BG_COLOR)
    probe_draw = ImageDraw.Draw(probe_img)

    # ---- Fit each text block ----
    header_font = ImageFont.truetype(FONT_HEADER, 34)

    arabic_font, arabic_lines = fit_arabic_font(
        verse["arabic"], content_width, probe_draw,
        min_size=34, max_size=82, max_lines=10
    )
    english_font, english_lines = fit_wrapped_font(
        verse["english"], content_width, probe_draw, FONT_ENGLISH,
        min_size=22, max_size=30, max_lines=8, rtl=False
    )
    urdu_font, urdu_lines = fit_wrapped_font(
        verse["urdu"], content_width, probe_draw, FONT_URDU,
        min_size=30, max_size=42, max_lines=8, rtl=True
    )

    # ---- Compute dynamic canvas height ----
    def block_height(lines, font, line_spacing_ratio=1.5):
        bbox = probe_draw.textbbox((0, 0), "Ay" if font.path != FONT_ARABIC else "بي", font=font)
        line_h = (bbox[3] - bbox[1]) * line_spacing_ratio
        return int(line_h * len(lines))

    header_h  = 60
    arabic_h  = block_height(arabic_lines, arabic_font, 1.7)
    english_h = block_height(english_lines, english_font, 1.4)
    urdu_h    = block_height(urdu_lines, urdu_font, 1.8)
    label_h   = 40   # small caption above each block
    divider_h = 30
    footer_h  = 70

    total_height = (
        PADDING
        + header_h + 30
        + label_h + arabic_h + divider_h
        + label_h + english_h + divider_h
        + label_h + urdu_h + divider_h
        + footer_h
        + PADDING
    )
    total_height = max(total_height, 700)  # sensible minimum

    # ---- Render final image ----
    img = Image.new("RGB", (CANVAS_WIDTH, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING

    # Header
    header_text = f"Surah {verse['surah_number']}: {verse['surah_name_en']}  ({verse['surah_name_ar']})  |  Ayah {verse['ayah_number']}"
    bbox = draw.textbbox((0, 0), header_text, font=header_font)
    header_w = bbox[2] - bbox[0]
    draw.text(((CANVAS_WIDTH - header_w) / 2, y), header_text, font=header_font, fill=ACCENT_COLOR)
    y += header_h

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=2)
    y += 30

    # Arabic label + block (right-aligned, bold, large)
    label_font = ImageFont.truetype(FONT_HEADER, 20)
    draw.text((CANVAS_WIDTH - PADDING, y), shape_arabic("النص العربي"), font=label_font,
               fill=ACCENT_COLOR, anchor="ra")
    y += label_h

    line_bbox = draw.textbbox((0, 0), "بي", font=arabic_font)
    arabic_line_h = int((line_bbox[3] - line_bbox[1]) * 1.7)
    for line in arabic_lines:
        draw.text((CANVAS_WIDTH - PADDING, y), line, font=arabic_font, fill=TEXT_COLOR, anchor="ra")
        y += arabic_line_h
    y += divider_h - 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    y += 20

    # English label + block (left-aligned, italic)
    draw.text((PADDING, y), "English — Sahih International", font=label_font, fill=ACCENT_COLOR)
    y += label_h
    eng_line_bbox = draw.textbbox((0, 0), "Ay", font=english_font)
    eng_line_h = int((eng_line_bbox[3] - eng_line_bbox[1]) * 1.4)
    for line in english_lines:
        draw.text((PADDING, y), line, font=english_font, fill=TEXT_COLOR)
        y += eng_line_h
    y += divider_h - 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=1)
    y += 20

    # Urdu label + block (right-aligned)
    draw.text((CANVAS_WIDTH - PADDING, y), "اردو ترجمہ — فتح محمد جالندھری", font=label_font,
               fill=ACCENT_COLOR, anchor="ra")
    y += label_h
    urdu_line_bbox = draw.textbbox((0, 0), "بی", font=urdu_font)
    urdu_line_h = int((urdu_line_bbox[3] - urdu_line_bbox[1]) * 1.8)
    for line in urdu_lines:
        draw.text((CANVAS_WIDTH - PADDING, y), line, font=urdu_font, fill=TEXT_COLOR, anchor="ra")
        y += urdu_line_h
    y += divider_h - 10

    draw.line([(PADDING, y), (CANVAS_WIDTH - PADDING, y)], fill=DIVIDER_COLOR, width=2)
    y += 25

    # Footer
    footer_font = ImageFont.truetype(FONT_ENGLISH, 22)
    footer_text = "May Allah guide us all. آمین"
    bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    footer_w = bbox[2] - bbox[0]
    draw.text(((CANVAS_WIDTH - footer_w) / 2, y), footer_text, font=footer_font, fill=(120, 120, 120))

    img.save(output_path, "PNG")
    print(f"✅ Image saved: {output_path} ({CANVAS_WIDTH}x{total_height})")


if __name__ == "__main__":
    # Quick manual test
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
