"""
تبدیل و قالب‌بندی تاریخ شمسی (هجری خورشیدی) — بدون هیچ کتابخانه بیرونی.

الگوریتم تبدیل، پیاده‌سازی استاندارد jalaali است و برای بازه ۱۱۷۸ تا ۱۶۳۳ شمسی
(۱۷۹۹ تا ۲۲۵۶ میلادی) دقیق است.
"""
from __future__ import annotations

import datetime as _dt
import re

MONTH_NAMES = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

WEEKDAY_NAMES = (
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
)

SEASON_NAMES = ("بهار", "تابستان", "پاییز", "زمستان")

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

_DIGIT_TRANSLATION = {}
for _i in range(10):
    _DIGIT_TRANSLATION[ord(PERSIAN_DIGITS[_i])] = str(_i)
    _DIGIT_TRANSLATION[ord(ARABIC_DIGITS[_i])] = str(_i)

_G_DAYS_IN_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


# --------------------------------------------------------------------------- #
#  ابزار رقم‌ها
# --------------------------------------------------------------------------- #
def to_english_digits(text) -> str:
    """تبدیل ارقام فارسی/عربی به ارقام لاتین."""
    if text is None:
        return ""
    return str(text).translate(_DIGIT_TRANSLATION)


def to_persian_digits(text) -> str:
    """تبدیل ارقام لاتین به ارقام فارسی."""
    if text is None:
        return ""
    out = []
    for ch in str(text):
        if "0" <= ch <= "9":
            out.append(PERSIAN_DIGITS[ord(ch) - 48])
        else:
            out.append(ch)
    return "".join(out)


# --------------------------------------------------------------------------- #
#  تبدیل تاریخ
# --------------------------------------------------------------------------- #
def gregorian_to_jalali(gy: int, gm: int, gd: int):
    """(۲۰۲۶, ۸, ۸) -> (۱۴۰۵, ۵, ۱۷)"""
    gy, gm, gd = int(gy), int(gm), int(gd)
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621

    gy2 = gy + 1 if gm > 2 else gy
    days = (
        (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        - 80
        + gd
        + _G_DAYS_IN_MONTH[gm - 1]
    )

    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int):
    """(۱۴۰۵, ۵, ۱۷) -> (۲۰۲۶, ۸, ۸)"""
    jy, jm, jd = int(jy), int(jm), int(jd)
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621

    days = (
        (365 * jy)
        + ((jy // 33) * 8)
        + (((jy % 33) + 3) // 4)
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186)
    )

    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    month_days = (0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 12
    for m in range(1, 13):
        if gd <= month_days[m]:
            gm = m
            break
        gd -= month_days[m]
    return gy, gm, gd


def is_jalali_leap(jy: int) -> bool:
    """سال کبیسه شمسی (اسفند ۳۰ روزه) — با آزمون رفت‌وبرگشت."""
    gy, gm, gd = jalali_to_gregorian(jy, 12, 30)
    return gregorian_to_jalali(gy, gm, gd) == (jy, 12, 30)


def jalali_month_days(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def is_valid_jalali(jy: int, jm: int, jd: int) -> bool:
    try:
        jy, jm, jd = int(jy), int(jm), int(jd)
    except (TypeError, ValueError):
        return False
    if not (1178 <= jy <= 1633):
        return False
    if not (1 <= jm <= 12):
        return False
    return 1 <= jd <= jalali_month_days(jy, jm)


def to_jalali(value) -> tuple:
    """از date/datetime به تاپل (سال، ماه، روز) شمسی."""
    if isinstance(value, _dt.datetime):
        value = value.date()
    return gregorian_to_jalali(value.year, value.month, value.day)


def to_date(jy: int, jm: int, jd: int) -> _dt.date:
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return _dt.date(gy, gm, gd)


# --------------------------------------------------------------------------- #
#  قالب‌بندی
# --------------------------------------------------------------------------- #
def format_jalali(value, persian_digits: bool = True) -> str:
    """۱۴۰۵/۰۵/۱۷"""
    if value is None:
        return ""
    jy, jm, jd = to_jalali(value)
    text = "%04d/%02d/%02d" % (jy, jm, jd)
    return to_persian_digits(text) if persian_digits else text


def format_jalali_long(value, persian_digits: bool = True) -> str:
    """۱۷ مرداد ۱۴۰۵"""
    if value is None:
        return ""
    jy, jm, jd = to_jalali(value)
    text = "%d %s %d" % (jd, MONTH_NAMES[jm - 1], jy)
    return to_persian_digits(text) if persian_digits else text


def format_jalali_full(value, persian_digits: bool = True) -> str:
    """شنبه ۱۷ مرداد ۱۴۰۵"""
    if value is None:
        return ""
    day = value.date() if isinstance(value, _dt.datetime) else value
    text = "%s %s" % (weekday_name(day), format_jalali_long(day, persian_digits=False))
    return to_persian_digits(text) if persian_digits else text


def weekday_name(value) -> str:
    """نام روز هفته فارسی (شنبه اولین روز)."""
    if isinstance(value, _dt.datetime):
        value = value.date()
    # python: دوشنبه=0 ... یکشنبه=6  →  شنبه=0 در تقویم ایرانی
    return WEEKDAY_NAMES[(value.weekday() + 2) % 7]


def month_name(jm: int) -> str:
    jm = int(jm)
    if 1 <= jm <= 12:
        return MONTH_NAMES[jm - 1]
    return ""


def season_name(jm: int) -> str:
    jm = int(jm)
    if 1 <= jm <= 12:
        return SEASON_NAMES[(jm - 1) // 3]
    return ""


def format_jalali_month(jy: int, jm: int, persian_digits: bool = True) -> str:
    """مرداد ۱۴۰۵"""
    text = "%s %d" % (month_name(jm), int(jy))
    return to_persian_digits(text) if persian_digits else text


# --------------------------------------------------------------------------- #
#  تجزیه ورودی کاربر
# --------------------------------------------------------------------------- #
_DATE_SPLIT_RE = re.compile(r"[^0-9]+")


def parse_jalali_date(text):
    """
    ورودی «۱۴۰۵/۵/۱۷» یا «1405-05-17» یا «1405.5.17» را به date میلادی تبدیل می‌کند.
    در صورت نامعتبر بودن None برمی‌گرداند.
    """
    if text is None:
        return None
    if isinstance(text, _dt.datetime):
        return text.date()
    if isinstance(text, _dt.date):
        return text

    raw = to_english_digits(str(text)).strip()
    if not raw:
        return None

    parts = [p for p in _DATE_SPLIT_RE.split(raw) if p]
    if len(parts) != 3:
        return None
    try:
        jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None

    # اگر کاربر سال دو رقمی داد (مثلاً ۰۵/۰۵/۱۷ یا ۱۷/۰۵/۰۵)
    if jy < 100:
        jy += 1400
    if not is_valid_jalali(jy, jm, jd):
        return None
    return to_date(jy, jm, jd)


def parse_time(text):
    """«۱۴:۳۰» یا «14:30:00» → datetime.time"""
    if text is None:
        return None
    if isinstance(text, _dt.time):
        return text
    raw = to_english_digits(str(text)).strip()
    if not raw:
        return None
    parts = [p for p in _DATE_SPLIT_RE.split(raw) if p]
    if not parts:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        return _dt.time(hour % 24, minute % 60, second % 60)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
#  بازه‌های زمانی آماده
# --------------------------------------------------------------------------- #
def jalali_month_range(jy: int, jm: int):
    """اولین و آخرین روز یک ماه شمسی به صورت date میلادی."""
    start = to_date(jy, jm, 1)
    end = to_date(jy, jm, jalali_month_days(jy, jm))
    return start, end


def jalali_year_range(jy: int):
    start = to_date(jy, 1, 1)
    end = to_date(jy, 12, jalali_month_days(jy, 12))
    return start, end


def week_range(today: _dt.date):
    """هفته ایرانی: شنبه تا جمعه."""
    offset = (today.weekday() + 2) % 7  # فاصله از شنبه
    start = today - _dt.timedelta(days=offset)
    return start, start + _dt.timedelta(days=6)


def add_jalali_months(jy: int, jm: int, delta: int):
    """جابه‌جایی روی ماه‌های شمسی (delta می‌تواند منفی باشد)."""
    total = (jy * 12) + (jm - 1) + delta
    return total // 12, (total % 12) + 1


def last_jalali_months(today: _dt.date, count: int = 6):
    """
    فهرست count ماه شمسی گذشته (شامل ماه جاری) به صورت
    [(jy, jm, start_date, end_date), ...] از قدیم به جدید.
    """
    jy, jm, _ = to_jalali(today)
    result = []
    for i in range(count - 1, -1, -1):
        y, m = add_jalali_months(jy, jm, -i)
        start, end = jalali_month_range(y, m)
        result.append((y, m, start, end))
    return result
