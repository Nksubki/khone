"""
تبدیل متن فارسی (تایپی یا گفتاری) به عدد، و نمایش عدد به شکل خوانا.

این ماژول دقیقاً معادل static/js/persian-number.js است تا نتیجه سمت سرور و
سمت مرورگر یکسان باشد. برای اطمینان: python tools/check_utils.py و node tools/check_js.js

نمونه‌های پشتیبانی‌شده:
    "100000000"                  -> 100000000
    "۱۰۰,۰۰۰,۰۰۰"                -> 100000000
    "100.000.000"                -> 100000000
    "صد میلیون"                  -> 100000000
    "صد و بیست میلیون"           -> 120000000
    "سی صد میلیون"               -> 300000000   (اصلاح خطای رایج تشخیص گفتار)
    "یک میلیون و نیم"            -> 1500000
    "نیم میلیارد"                -> 500000000
    "۲.۵ میلیون" / "۲/۵ میلیون"  -> 2500000
    "دویست و پنجاه میلیون تومان بابت میلگرد" -> 250000000
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
    "ونیم": 0.5,
    "ربع": 0.25,
}

SCALES = {
    "هزار": 1_000,
    "هزارتا": 1_000,
    "هزاری": 1_000,
    "هزارتومان": 1_000,
    "هزارتومن": 1_000,
    "میلیون": 1_000_000,
    "ملیون": 1_000_000,
    "میلیونی": 1_000_000,
    "ملیونی": 1_000_000,
    "میلیارد": 1_000_000_000,
    "ملیارد": 1_000_000_000,
    "میلیاردی": 1_000_000_000,
    "میلیارت": 1_000_000_000,
    "بیلیون": 1_000_000_000,
    "تریلیون": 1_000_000_000_000,
}

# واژه‌هایی که در محاسبه نادیده گرفته می‌شوند
IGNORED = {
    "و",
    "تومان",
    "تومن",
    "تومانه",
    "تومنه",
    "ریال",
    "مبلغ",
    "حدود",
    "تقریبا",
    "تقریباً",
    "شد",
    "شده",
    "است",
    "بود",
    "بشه",
    "کردم",
    "کن",
    "بنویس",
    "ثبت",
    "لطفا",
    "لطفاً",
    "دادم",
    "پرداخت",
    "پول",
    "تا",
    "بابت",
    "برای",
    "هزینه",
    "خرید",
    "بشود",
    "میشه",
}

# اصلاح خطاهای رایج تشخیص گفتار (واژه‌های چندپاره)
SPLIT_FIXES = (
    ("یک صد", "صد"),
    ("دو صد", "دویست"),
    ("دو یست", "دویست"),
    ("سه صد", "سیصد"),
    ("سی صد", "سیصد"),
    ("چهار صد", "چهارصد"),
    ("پنج صد", "پانصد"),
    ("پان صد", "پانصد"),
    ("پون صد", "پانصد"),
    ("شش صد", "ششصد"),
    ("شیش صد", "ششصد"),
    ("هفت صد", "هفتصد"),
    ("هشت صد", "هشتصد"),
    ("نه صد", "نهصد"),
    ("پان زده", "پانزده"),
    ("شان زده", "شانزده"),
    ("و نیم", "ونیم"),
    ("میلیون ها", "میلیون"),
    ("میلیارد ها", "میلیارد"),
)

# سقف منطقی برای مبلغ (یک کوادریلیون تومان)
MAX_AMOUNT = 10 ** 15

_ZWNJ = "\u200c"
_CLEAN_RE = re.compile(r"[^\w\s./]", re.UNICODE)
_NUMERIC_RE = re.compile(r"^\d+(?:\.\d+)?$")
_THOUSAND_DOT_RE = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
_SLASH_DECIMAL_RE = re.compile(r"^\d+/\d{1,2}$")


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
        .replace("آ", "ا")
        .replace("ؤ", "و")
        .replace("٫", ".")
        .replace("\u064b", "")
        .replace("\u064c", "")
        .replace("\u064d", "")
        .replace("\u064e", "")
        .replace("\u064f", "")
        .replace("\u0650", "")
        .replace("\u0651", "")
        .replace("\u0652", "")
    )
    return re.sub(r"\s+", " ", out).strip()


def _apply_split_fixes(text: str) -> str:
    padded = " %s " % text
    for src, dst in SPLIT_FIXES:
        padded = padded.replace(" %s " % src, " %s " % dst)
    return padded.strip()


def _numeric_value(token: str):
    """مقدار عددی یک توکن رقمی (با پشتیبانی از جداکننده هزارگان و اعشار)."""
    if _THOUSAND_DOT_RE.match(token):
        return float(token.replace(".", ""))
    if _NUMERIC_RE.match(token):
        return float(token)
    if _SLASH_DECIMAL_RE.match(token):
        return float(token.replace("/", "."))
    return None


def _tokenize(text: str):
    text = normalize_text(text)
    text = text.replace("،", " ").replace(",", "")
    text = text.replace(_ZWNJ, " ")
    text = _CLEAN_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = _apply_split_fixes(text)

    tokens = []
    for raw in text.split():
        token = raw.strip(".")
        if not token:
            continue
        # چسبیدن «و» به کلمه بعدی: مثل «وبیست» یا «ونیم»
        if len(token) > 2 and token.startswith("و"):
            rest = token[1:]
            if rest in UNITS or rest in SCALES:
                tokens.append(rest)
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
        value = int(round(text))
        return value if 0 < value <= MAX_AMOUNT else None

    tokens = _tokenize(text)
    if not tokens:
        return None

    total = 0.0
    current = 0.0
    last_scale = 0
    found = False

    for token in tokens:
        if token in IGNORED:
            continue

        numeric = _numeric_value(token)
        if numeric is not None:
            current += numeric
            found = True
            continue

        if token in UNITS:
            current += UNITS[token]
            found = True
            continue

        if token in FRACTIONS:
            fraction = FRACTIONS[token]
            if current == 0 and last_scale >= 1000:
                # «یک میلیون و نیم» → نیمِ آخرین مقیاس
                total += fraction * last_scale
            else:
                current = current + fraction if current else fraction
            found = True
            continue

        if token in SCALES:
            scale = SCALES[token]
            if current == 0:
                current = 1.0
            current *= scale
            total += current
            current = 0.0
            last_scale = scale
            found = True
            continue

        # ترکیب چسبیده مثل «صدمیلیون» یا «۵۰۰هزار»
        matched = False
        for word, scale in SCALES.items():
            if token.endswith(word) and len(token) > len(word):
                head = token[: -len(word)]
                head_value = _numeric_value(head)
                if head_value is None and head in UNITS:
                    head_value = float(UNITS[head])
                if head_value is None and head in FRACTIONS:
                    head_value = FRACTIONS[head]
                if head_value is not None:
                    current = (current + head_value) * scale
                    total += current
                    current = 0.0
                    last_scale = scale
                    found = True
                    matched = True
                    break
        if matched:
            continue
        # واژه ناشناخته: نادیده گرفته می‌شود

    if not found:
        return None

    total += current
    if total <= 0 or total > MAX_AMOUNT:
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


def roundness_score(value) -> int:
    """
    امتیاز «گرد بودن» یک مبلغ — برای انتخاب بهترین حدس بین چند نتیجه تشخیص گفتار.
    مبالغ واقعی هزینه معمولاً گرد هستند (مضرب هزار یا میلیون).
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    if number <= 0:
        return 0
    score = 0
    for scale, points in ((1_000_000, 3), (100_000, 2), (10_000, 1), (1_000, 1)):
        if number % scale == 0:
            score += points
    return score
