"""
تبدیل متن فارسی (تایپی یا گفتاری) به عدد، و نمایش عدد به شکل خوانا.

نمونه‌های پشتیبانی‌شده:
    "100000000"            -> 100000000
    "۱۰۰,۰۰۰,۰۰۰"          -> 100000000
    "صد میلیون"            -> 100000000
    "صد و بیست میلیون"     -> 120000000
    "دو میلیارد و سیصد میلیون و پانصد هزار تومان" -> 2300500000
    "۱۰۰ میلیون"           -> 100000000
    "نیم میلیارد"          -> 500000000
    "۲.۵ میلیون"           -> 2500000
"""
from __future__ import annotations

import re

from .jalali import to_english_digits, to_persian_digits

# --------------------------------------------------------------------------- #
#  واژه‌نامه اعداد فارسی
# --------------------------------------------------------------------------- #
UNITS = {
    "صفر": 0,
    "یک": 1,
    "اول": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "پنج": 5,
    "شش": 6,
    "شیش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,
    "ده": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "پونزده": 15,
    "شانزده": 16,
    "شونزده": 16,
    "هفده": 17,
    "هیفده": 17,
    "هجده": 18,
    "هیجده": 18,
    "نوزده": 19,
    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
    "صد": 100,
    "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
    "پونصد": 500,
    "ششصد": 600,
    "شیشصد": 600,
    "هفتصد": 700,
    "هفصد": 700,
    "هشتصد": 800,
    "نهصد": 900,
}

FRACTIONS = {
    "نیم": 0.5,
    "ربع": 0.25,
}

SCALES = {
    "هزار": 1_000,
    "هزارتا": 1_000,
    "میلیون": 1_000_000,
    "ملیون": 1_000_000,
    "میلیارد": 1_000_000_000,
    "ملیارد": 1_000_000_000,
    "بیلیون": 1_000_000_000,
    "تریلیون": 1_000_000_000_000,
}

# واژه‌هایی که نادیده گرفته می‌شوند
IGNORED = {
    "و",
    "تومان",
    "تومن",
    "ریال",
    "هزارتومان",
    "مبلغ",
    "حدود",
    "تقریبا",
    "تقریباً",
    "شد",
    "شده",
    "است",
    "بود",
    "کردم",
    "دادم",
    "پرداخت",
    "پول",
    "تا",
}

_ZWNJ = "\u200c"
_CLEAN_RE = re.compile(r"[^\w\s./]", re.UNICODE)
_NUMERIC_RE = re.compile(r"^\d+(?:\.\d+)?$")


def normalize_text(text) -> str:
    """یکسان‌سازی حروف عربی/فارسی و ارقام."""
    if text is None:
        return ""
    out = to_english_digits(str(text))
    out = (
        out.replace("ي", "ی")
        .replace("ك", "ک")
        .replace("ة", "ه")
        .replace("ۀ", "ه")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("ؤ", "و")
        .replace("\u064b", "")
        .replace("\u064c", "")
        .replace("\u064d", "")
        .replace("\u064e", "")
        .replace("\u064f", "")
        .replace("\u0650", "")
        .replace("\u0651", "")
        .replace("\u0652", "")
    )
    return out.strip()


def _tokenize(text: str):
    text = normalize_text(text)
    text = text.replace("،", " ").replace(",", "")
    text = text.replace(_ZWNJ, "")
    text = _CLEAN_RE.sub(" ", text)
    tokens = []
    for raw in text.split():
        token = raw.strip(".")
        if not token:
            continue
        # چسبیدن «و» به کلمه بعدی: مثل «وبیست»
        if len(token) > 2 and token.startswith("و") and token[1:] in UNITS:
            tokens.append(token[1:])
            continue
        tokens.append(token)
    return tokens


def parse_amount(text):
    """
    متن را به عدد صحیح (تومان) تبدیل می‌کند.
    اگر هیچ عددی پیدا نشود None برمی‌گرداند.
    """
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return int(round(text))

    tokens = _tokenize(text)
    if not tokens:
        return None

    total = 0.0
    current = 0.0
    found = False

    for token in tokens:
        if token in IGNORED:
            continue

        if _NUMERIC_RE.match(token):
            current += float(token)
            found = True
            continue

        if token in UNITS:
            current += UNITS[token]
            found = True
            continue

        if token in FRACTIONS:
            current = current + FRACTIONS[token] if current else FRACTIONS[token]
            found = True
            continue

        if token in SCALES:
            scale = SCALES[token]
            if current == 0:
                current = 1.0
            current *= scale
            total += current
            current = 0.0
            found = True
            continue

        # ترکیب چسبیده مثل «صدمیلیون» یا «۵۰۰هزار»
        matched = False
        for word, scale in SCALES.items():
            if token.endswith(word) and len(token) > len(word):
                head = token[: -len(word)]
                head_value = None
                if _NUMERIC_RE.match(head):
                    head_value = float(head)
                elif head in UNITS:
                    head_value = float(UNITS[head])
                elif head in FRACTIONS:
                    head_value = FRACTIONS[head]
                if head_value is not None:
                    current = (current + head_value) * scale
                    total += current
                    current = 0.0
                    found = True
                    matched = True
                    break
        if matched:
            continue
        # واژه ناشناخته: نادیده گرفته می‌شود

    if not found:
        return None

    total += current
    if total <= 0:
        return None
    return int(round(total))


# --------------------------------------------------------------------------- #
#  نمایش
# --------------------------------------------------------------------------- #
def group_digits(value) -> str:
    """۱۲۳۴۵۶۷ -> «1,234,567»"""
    if value in (None, ""):
        return ""
    try:
        number = int(round(float(to_english_digits(str(value)).replace(",", ""))))
    except (TypeError, ValueError):
        return str(value)
    return "{:,}".format(number)


def format_money(value, persian: bool = True) -> str:
    text = group_digits(value)
    return to_persian_digits(text) if persian else text


_WORD_SCALES = (
    (1_000_000_000_000, "هزار میلیارد"),
    (1_000_000_000, "میلیارد"),
    (1_000_000, "میلیون"),
    (1_000, "هزار"),
)


def humanize_amount(value, persian: bool = True) -> str:
    """
    ۲۳۰۵۰۰۰۰۰ -> «۲۳۰ میلیون و ۵۰۰ هزار»
    برای تأیید سریع مبلغ توسط کاربر (خصوصاً وقتی با صدا وارد شده).
    """
    if value in (None, ""):
        return ""
    try:
        number = int(round(float(to_english_digits(str(value)).replace(",", ""))))
    except (TypeError, ValueError):
        return ""
    if number == 0:
        return to_persian_digits("0") if persian else "0"

    negative = number < 0
    number = abs(number)
    parts = []
    for scale, label in _WORD_SCALES:
        if number >= scale:
            count = number // scale
            number %= scale
            parts.append("%d %s" % (count, label))
    if number:
        parts.append("%d" % number)

    text = " و ".join(parts)
    if negative:
        text = "منفی " + text
    return to_persian_digits(text) if persian else text
