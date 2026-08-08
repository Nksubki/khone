"""
تست سلامت ماژول‌های تاریخ شمسی و پارسر عدد فارسی — بدون نیاز به جنگو.

اجرا:
    python tools/check_utils.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledger.utils import jalali as J  # noqa: E402
from ledger.utils import numbers as N  # noqa: E402

failures = []


def check(condition, message):
    if not condition:
        failures.append(message)
        print("  ✗ " + message)
    return condition


print("۱) تاریخ‌های مرجع")
KNOWN = [
    ((2026, 3, 21), (1405, 1, 1)),
    ((2026, 8, 8), (1405, 5, 17)),
    ((2025, 3, 21), (1404, 1, 1)),
    ((2024, 3, 20), (1403, 1, 1)),
    ((2021, 3, 21), (1400, 1, 1)),
    ((2000, 1, 1), (1378, 10, 11)),
    ((1979, 2, 11), (1357, 11, 22)),
    ((2024, 12, 31), (1403, 10, 11)),
    ((2016, 2, 29), (1394, 12, 10)),
]
for g, j in KNOWN:
    check(J.gregorian_to_jalali(*g) == j, "g2j %s != %s (%s)" % (g, j, J.gregorian_to_jalali(*g)))
    check(J.jalali_to_gregorian(*j) == g, "j2g %s != %s (%s)" % (j, g, J.jalali_to_gregorian(*j)))

print("۲) رفت و برگشت ۱۹۰۰ تا ۲۱۰۰")
day = datetime.date(1900, 1, 1)
end = datetime.date(2100, 1, 1)
bad = 0
while day < end:
    jy, jm, jd = J.gregorian_to_jalali(day.year, day.month, day.day)
    if J.jalali_to_gregorian(jy, jm, jd) != (day.year, day.month, day.day):
        bad += 1
    if not J.is_valid_jalali(jy, jm, jd):
        bad += 1
    day += datetime.timedelta(days=1)
check(bad == 0, "خطای رفت‌وبرگشت: %d" % bad)

print("۳) سال‌های کبیسه و طول ماه‌ها")
for year in range(1380, 1430):
    total = sum(J.jalali_month_days(year, m) for m in range(1, 13))
    expected = 366 if J.is_jalali_leap(year) else 365
    check(total == expected, "طول سال %d = %d" % (year, total))
print("   کبیسه‌های ۱۳۹۰ تا ۱۴۲۰: %s" % [y for y in range(1390, 1421) if J.is_jalali_leap(y)])

print("۴) روز هفته")
check(J.weekday_name(datetime.date(2026, 8, 8)) == "شنبه", "شنبه")
check(J.weekday_name(datetime.date(2026, 8, 9)) == "یکشنبه", "یکشنبه")
check(J.weekday_name(datetime.date(2026, 8, 14)) == "جمعه", "جمعه")

print("۵) تجزیه تاریخ")
target = datetime.date(2026, 8, 8)
for text in ("۱۴۰۵/۰۵/۱۷", "1405-5-17", "1405.05.17", " ۱۴۰۵ / ۵ / ۱۷ "):
    check(J.parse_jalali_date(text) == target, "parse %r" % text)
for text in ("1405/13/01", "1405/12/31", "سلام", "", None):
    check(J.parse_jalali_date(text) is None, "باید None باشد: %r" % text)

print("۶) عدد فارسی")
CASES = [
    ("100000000", 100000000),
    ("۱۰۰,۰۰۰,۰۰۰", 100000000),
    ("صد میلیون", 100000000),
    ("صد و بیست میلیون", 120000000),
    ("دو میلیارد و سیصد میلیون و پانصد هزار تومان", 2300500000),
    ("۱۰۰ میلیون", 100000000),
    ("نیم میلیارد", 500000000),
    ("۲.۵ میلیون", 2500000),
    ("پنجاه و پنج میلیون و دویست هزار تومان", 55200000),
    ("سه میلیون تومان", 3000000),
    ("یک میلیارد", 1000000000),
    ("هفتصد و پنجاه هزار", 750000),
    ("صدمیلیون", 100000000),
    ("500هزار", 500000),
    ("بیست و پنج", 25),
    ("مبلغ سی و دو میلیون و هشتصد و پنجاه هزار تومان شد", 32850000),
    ("چهارصد و پنجاه میلیون", 450000000),
    ("یک میلیون و پانصد هزار", 1500000),
    ("سلام خوبی", None),
    ("", None),
]
for text, expected in CASES:
    got = N.parse_amount(text)
    check(got == expected, "parse_amount(%r) = %r ≠ %r" % (text, got, expected))

print("۷) نمایش مبلغ")
check(N.format_money(1234567) == "۱,۲۳۴,۵۶۷", "format_money")
check(N.humanize_amount(230500000) == "۲۳۰ میلیون و ۵۰۰ هزار", "humanize: %s" % N.humanize_amount(230500000))
check(N.humanize_amount(2300500000) == "۲ میلیارد و ۳۰۰ میلیون و ۵۰۰ هزار", "humanize2")

print()
if failures:
    print("نتیجه: %d خطا" % len(failures))
    sys.exit(1)
print("نتیجه: همه تست‌ها موفق ✓")
