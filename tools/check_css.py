"""
بررسی سلامت و خوانایی فایل CSS — بدون نیاز به مرورگر.

چه چیزهایی بررسی می‌شود؟
  • تراز بودن آکولادها و نبودن خطای ساختاری
  • فهرست بریک‌پوینت‌ها و نبودن حفره بین آن‌ها
  • فونت‌های خیلی ریز (برای خوانایی افراد کم‌بینا)
  • اندازه‌های ثابت پیکسلی که در گوشی باریک بیرون می‌زنند
  • حداقل اندازه فیلدهای ورودی (جلوگیری از زوم خودکار آیفون)

اجرا:
    python tools/check_css.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "static", "css", "app.css")

MIN_READABLE_REM = 0.78          # کوچک‌ترین اندازه مجاز متن
SMALL_SCREEN_PX = 320            # باریک‌ترین گوشی هدف

errors = []
warnings = []

with open(CSS_PATH, encoding="utf-8") as handle:
    css = handle.read()

lines = css.split("\n")

# --------------------------------------------------------------------------- #
print("۱) ساختار فایل")
# حذف کامنت‌ها برای شمارش دقیق
stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
open_braces = stripped.count("{")
close_braces = stripped.count("}")
if open_braces != close_braces:
    errors.append("آکولادها تراز نیستند: %d باز و %d بسته" % (open_braces, close_braces))
print("   %d قاعده، %d خط" % (open_braces, len(lines)))

for index, line in enumerate(lines, start=1):
    if line.count("(") != line.count(")") and not line.strip().startswith("/*"):
        # فقط خطوطی که کامل در یک خط هستند بررسی می‌شوند
        if line.strip().endswith(";") or line.strip().endswith("{"):
            errors.append("پرانتز نامتوازن در خط %d: %s" % (index, line.strip()[:70]))

# --------------------------------------------------------------------------- #
print("۲) بریک‌پوینت‌ها")
media_conditions = " | ".join(re.findall(r"@media([^{]+)\{", css))
min_widths = sorted({int(m) for m in re.findall(r"min-width:\s*(\d+)px", media_conditions)})
max_widths = sorted({int(m) for m in re.findall(r"max-width:\s*(\d+)(?:\.\d+)?px", media_conditions)})
print("   min-width: %s" % ", ".join(str(w) for w in min_widths))
print("   max-width: %s" % ", ".join(str(w) for w in max_widths))

if not min_widths:
    errors.append("هیچ بریک‌پوینت min-width تعریف نشده است.")
else:
    # نباید بین بریک‌پوینت‌ها فاصله بزرگ‌تر از ۳۵۰ پیکسل باشد
    previous = min_widths[0]
    for width in min_widths[1:]:
        if width - previous > 350:
            warnings.append("فاصله زیاد بین بریک‌پوینت %d و %d" % (previous, width))
        previous = width
    if min_widths[0] > 520:
        warnings.append("اولین بریک‌پوینت (%d) برای موبایل بزرگ دیر است." % min_widths[0])

for width in max_widths:
    if width in min_widths:
        warnings.append(
            "بریک‌پوینت %dpx هم در min-width و هم max-width هست (احتمال هم‌پوشانی)." % width
        )

# --------------------------------------------------------------------------- #
print("۳) خوانایی متن‌ها")
tiny = []
for index, line in enumerate(lines, start=1):
    for match in re.finditer(r"font-size:\s*([\d.]+)rem", line):
        value = float(match.group(1))
        if value < MIN_READABLE_REM:
            selector = "خط %d" % index
            # پیدا کردن آخرین سلکتور بالای این خط
            for back in range(index - 1, max(0, index - 40), -1):
                if "{" in lines[back - 1] and "@" not in lines[back - 1]:
                    selector = lines[back - 1].split("{")[0].strip()
                    break
            tiny.append("%s → %srem (خط %d)" % (selector, match.group(1), index))
if tiny:
    for item in tiny:
        warnings.append("متن ریز: %s" % item)
else:
    print("   هیچ متنی کوچک‌تر از %srem نیست ✓" % MIN_READABLE_REM)

# --------------------------------------------------------------------------- #
print("۴) اندازه‌های ثابت پیکسلی")
risky = []
for index, line in enumerate(lines, start=1):
    for match in re.finditer(r"(?:^|[\s:])(?:width|min-width):\s*(\d{3,})px", line):
        value = int(match.group(1))
        if value > SMALL_SCREEN_PX - 40 and "max-width" not in line and "@media" not in line:
            risky.append("خط %d: %s" % (index, line.strip()[:70]))
if risky:
    for item in risky:
        errors.append("عرض ثابت خطرناک برای گوشی باریک — %s" % item)
else:
    print("   هیچ عرض ثابت خطرناکی پیدا نشد ✓")

# --------------------------------------------------------------------------- #
print("۵) اندازه فیلدهای ورودی (زوم خودکار آیفون)")
field_rule = re.search(r"\.field-input\s*\{(.*?)\}", css, re.S)
if not field_rule:
    errors.append("قاعده .field-input پیدا نشد.")
else:
    body = field_rule.group(1)
    if "max(16px" not in body.replace(" ", "").replace("max(16px,", "max(16px,"):
        if "max(16px" not in body:
            errors.append(
                ".field-input باید حداقل ۱۶ پیکسل باشد (font-size: max(16px, ...)) "
                "وگرنه سافاری آیفون هنگام لمس فیلد زوم می‌کند."
            )
    if "max(16px" in body:
        print("   حداقل ۱۶ پیکسل رعایت شده ✓")

# --------------------------------------------------------------------------- #
print("۶) نکات موبایل")
required = {
    "env(safe-area-inset-bottom)": "فاصله امن پایین صفحه (آیفون با نوار خانه)",
    "100dvh": "ارتفاع درست در سافاری موبایل",
    "-webkit-overflow-scrolling": "اسکرول نرم در iOS",
    "-webkit-backdrop-filter": "پس‌زمینه شیشه‌ای در سافاری",
    "overscroll-behavior": "جلوگیری از اسکرول زنجیره‌ای منو",
    "touch-action: manipulation": "حذف تأخیر لمس دکمه‌ها",
}
for needle, label in required.items():
    if needle not in css:
        warnings.append("%s استفاده نشده است (%s)" % (needle, label))
    else:
        print("   %s ✓" % label)

# --------------------------------------------------------------------------- #
print("۷) مقیاس اندازه متن")
for level in ("sm", "md", "lg", "xl", "xxl"):
    if "data-font='%s'" % level not in css and 'data-font="%s"' % level not in css:
        errors.append("سطح اندازه متن «%s» در CSS تعریف نشده است." % level)
scales = re.findall(r"html\[data-font='(\w+)'\]\s*\{\s*font-size:\s*([\d.]+)%", css)
if scales:
    print("   " + " · ".join("%s=%s%%" % (name, value) for name, value in scales))

print()
for warning in warnings:
    print("⚠ " + warning)
if errors:
    print("\nنتیجه: %d خطا" % len(errors))
    for error in errors:
        print("  ✗ " + error)
    sys.exit(1)
print("نتیجه: CSS سالم و خوانا است ✓")
