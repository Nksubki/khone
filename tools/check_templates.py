"""
بررسی ایستای قالب‌ها و مسیرها (بدون نیاز به نصب جنگو).

چه چیزهایی بررسی می‌شود؟
  • وجود همه قالب‌های ارجاع‌شده در extends / include / render
  • درست بودن نام همه {% url '...' %}ها بر اساس ledger/urls.py
  • تراز بودن تگ‌های بلوکی (if/for/block/with/…)
  • ثبت‌شده بودن همه فیلترها و تگ‌های استفاده‌شده
  • وجود همه ویوهای نام‌برده در urls.py

اجرا:
    python tools/check_templates.py
"""
import os
import re
import sys
from xml.etree import ElementTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT, "templates")
LEDGER_DIR = os.path.join(ROOT, "ledger")

errors = []
warnings = []


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------- #
#  جمع‌آوری اطلاعات پروژه
# --------------------------------------------------------------------------- #
urls_source = read(os.path.join(LEDGER_DIR, "urls.py"))
url_names = set(re.findall(r'name="([^"]+)"', urls_source))
url_views = set(re.findall(r"views\.(\w+)", urls_source))

views_source = read(os.path.join(LEDGER_DIR, "views.py"))
view_functions = set(re.findall(r"^def (\w+)\(", views_source, re.M))

fa_source = read(os.path.join(LEDGER_DIR, "templatetags", "fa.py"))
custom_filters = set(re.findall(r'@register\.filter\(name="([^"]+)"\)', fa_source))
custom_filters |= set(re.findall(r"@register\.filter\s*\ndef (\w+)", fa_source))
custom_tags = set(re.findall(r"@register\.simple_tag[^\n]*\ndef (\w+)", fa_source))
custom_tags |= set(re.findall(r'@register\.simple_tag\([^)]*name="([^"]+)"', fa_source))
custom_tags |= set(re.findall(r'@register\.inclusion_tag\([^)]*name="([^"]+)"', fa_source))

BUILTIN_FILTERS = {
    "add", "addslashes", "capfirst", "center", "cut", "date", "default",
    "default_if_none", "dictsort", "dictsortreversed", "divisibleby", "escape",
    "escapejs", "filesizeformat", "first", "floatformat", "force_escape", "get_digit",
    "iriencode", "join", "json_script", "last", "length", "length_is", "linebreaks",
    "linebreaksbr", "linenumbers", "ljust", "lower", "make_list", "phone2numeric",
    "pluralize", "pprint", "random", "rjust", "safe", "safeseq", "slice", "slugify",
    "stringformat", "striptags", "time", "timesince", "timeuntil", "title",
    "truncatechars", "truncatechars_html", "truncatewords", "truncatewords_html",
    "unordered_list", "upper", "urlencode", "urlize", "urlizetrunc", "wordcount",
    "wordwrap", "yesno",
}

BUILTIN_TAGS = {
    "autoescape", "block", "comment", "csrf_token", "cycle", "debug", "extends",
    "filter", "firstof", "for", "if", "ifchanged", "include", "load", "lorem",
    "now", "querystring", "regroup", "resetcycle", "spaceless", "templatetag",
    "url", "verbatim", "widthratio", "with", "elif", "else", "empty",
    "static", "get_static_prefix", "get_media_prefix",
}

BLOCK_TAGS = {
    "if": "endif",
    "for": "endfor",
    "block": "endblock",
    "with": "endwith",
    "filter": "endfilter",
    "autoescape": "endautoescape",
    "spaceless": "endspaceless",
    "comment": "endcomment",
    "verbatim": "endverbatim",
    "ifchanged": "endifchanged",
    "blocktrans": "endblocktrans",
    "blocktranslate": "endblocktranslate",
}

MID_TAGS = {"else", "elif", "empty"}

# --------------------------------------------------------------------------- #
#  فهرست قالب‌ها
# --------------------------------------------------------------------------- #
template_files = []
for base, _dirs, files in os.walk(TEMPLATES_DIR):
    for name in files:
        if name.endswith(".html"):
            full = os.path.join(base, name)
            template_files.append(os.path.relpath(full, TEMPLATES_DIR).replace(os.sep, "/"))

template_set = set(template_files)

print("۱) ویوهای ارجاع‌شده در urls.py")
for name in sorted(url_views):
    if name not in view_functions:
        errors.append("ویو %s در urls.py آمده اما در views.py نیست." % name)
print("   %d مسیر، %d ویو" % (len(url_names), len(url_views)))

print("۲) قالب‌های ارجاع‌شده در views.py")
for match in re.finditer(r'render\(\s*request,\s*["\']([^"\']+)["\']', views_source):
    name = match.group(1)
    if name not in template_set:
        errors.append("قالب %s در views.py صدا زده شده اما فایلش نیست." % name)

TAG_RE = re.compile(r"{%\s*(\w+)([^%]*)%}")
FILTER_RE = re.compile(r"\|\s*([a-zA-Z_][\w]*)")
URL_RE = re.compile(r"{%\s*url\s+['\"]([^'\"]+)['\"]")
EXTENDS_RE = re.compile(r"{%\s*extends\s+['\"]([^'\"]+)['\"]")
INCLUDE_RE = re.compile(r"{%\s*include\s+['\"]([^'\"]+)['\"]")

print("۳) بررسی هر قالب")
for relative in sorted(template_files):
    path = os.path.join(TEMPLATES_DIR, relative)
    source = read(path)
    loaded = set()
    for match in re.finditer(r"{%\s*load\s+([^%]+)%}", source):
        loaded.update(match.group(1).split())

    # --- extends / include
    for name in EXTENDS_RE.findall(source) + INCLUDE_RE.findall(source):
        if name not in template_set:
            errors.append("%s: قالب ارجاع‌شده «%s» وجود ندارد." % (relative, name))

    # --- نام مسیرها
    for name in URL_RE.findall(source):
        target = name.split(":")[-1]
        if name.startswith("ledger:") and target not in url_names:
            errors.append("%s: نام مسیر «%s» در urls.py نیست." % (relative, name))

    # --- تراز تگ‌های بلوکی
    stack = []
    for match in TAG_RE.finditer(source):
        tag = match.group(1)
        if tag in BLOCK_TAGS:
            stack.append((tag, match.start()))
        elif tag.startswith("end"):
            expected = tag
            if not stack:
                errors.append("%s: تگ اضافی {%% %s %%}" % (relative, tag))
                continue
            open_tag, _pos = stack.pop()
            if BLOCK_TAGS.get(open_tag) != expected:
                errors.append(
                    "%s: {%% %s %%} با {%% %s %%} بسته شده است."
                    % (relative, open_tag, tag)
                )
    for open_tag, _pos in stack:
        errors.append("%s: تگ {%% %s %%} بسته نشده است." % (relative, open_tag))

    # --- تگ‌های ناشناخته
    for match in TAG_RE.finditer(source):
        tag = match.group(1)
        if tag.startswith("end") or tag in MID_TAGS:
            continue
        if tag in BUILTIN_TAGS:
            continue
        if tag in custom_tags:
            if "fa" not in loaded:
                errors.append("%s: تگ «%s» استفاده شده اما {%% load fa %%} ندارد." % (relative, tag))
            continue
        errors.append("%s: تگ ناشناخته {%% %s %%}" % (relative, tag))

    # --- فیلترها
    for name in set(FILTER_RE.findall(source)):
        if name in BUILTIN_FILTERS:
            continue
        if name in custom_filters:
            if "fa" not in loaded:
                errors.append("%s: فیلتر «%s» استفاده شده اما {%% load fa %%} ندارد." % (relative, name))
            continue
        errors.append("%s: فیلتر ناشناخته «%s»" % (relative, name))

    # --- static
    if "{% static" in source and "static" not in loaded:
        errors.append("%s: از static استفاده شده اما {%% load static %%} ندارد." % relative)

print("   %d قالب بررسی شد" % len(template_files))

print("۴) فایل‌های استاتیک ارجاع‌شده")
for relative in template_files:
    source = read(os.path.join(TEMPLATES_DIR, relative))
    for name in re.findall(r"{%\s*static\s+['\"]([^'\"]+)['\"]", source):
        if not os.path.exists(os.path.join(ROOT, "static", name)):
            errors.append("%s: فایل استاتیک «%s» موجود نیست." % (relative, name))

print("۵) آیکن‌های SVG")
sprite_source = read(os.path.join(TEMPLATES_DIR, "ledger", "partials", "_sprite.html"))
sprite_keys = set(re.findall(r'<symbol id="i-([\w-]+)"', sprite_source))
print("   %d آیکن در اسپرایت" % len(sprite_keys))

# اعتبارسنجی XML اسپرایت و هر symbol
SVG_NS = "{http://www.w3.org/2000/svg}"
ALLOWED_SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "g"}
try:
    sprite_root = ElementTree.fromstring(sprite_source[sprite_source.index("<svg"):])
    symbols = sprite_root.findall(SVG_NS + "symbol")
    if len(symbols) != len(sprite_keys):
        errors.append("تعداد symbolها با شناسه‌های یافت‌شده جور نیست.")
    for symbol in symbols:
        name = symbol.get("id")
        if not symbol.get("viewBox"):
            errors.append("آیکن %s ویژگی viewBox ندارد." % name)
        if not list(symbol):
            errors.append("آیکن %s خالی است." % name)
        for shape in symbol:
            tag = shape.tag.replace(SVG_NS, "")
            if tag not in ALLOWED_SHAPES:
                errors.append("آیکن %s عنصر ناشناخته <%s> دارد." % (name, tag))
            if tag == "path" and not (shape.get("d") or "").strip().startswith(("M", "m")):
                errors.append("آیکن %s مسیر نامعتبر دارد." % name)
except (ElementTree.ParseError, ValueError) as exc:
    errors.append("اسپرایت SVG معتبر نیست: %s" % exc)

favicon_path = os.path.join(ROOT, "static", "img", "favicon.svg")
if os.path.exists(favicon_path):
    try:
        ElementTree.fromstring(read(favicon_path))
    except ElementTree.ParseError as exc:
        errors.append("favicon.svg معتبر نیست: %s" % exc)
else:
    errors.append("static/img/favicon.svg موجود نیست.")

sys.path.insert(0, ROOT)
from ledger.icons import CATEGORY_ICONS, ICON_KEYS  # noqa: E402

for key in sorted(ICON_KEYS):
    if key not in sprite_keys:
        errors.append("آیکن «%s» در icons.py هست ولی در اسپرایت نیست." % key)
print("   %d آیکن اعلام‌شده در icons.py (%d آیکن دسته‌بندی)" % (len(ICON_KEYS), len(CATEGORY_ICONS)))

# آیکن‌های استفاده‌شده با نام ثابت در قالب‌ها
for relative in template_files:
    source = read(os.path.join(TEMPLATES_DIR, relative))
    for key in re.findall(r'{%\s*icon\s+"([\w-]+)"', source):
        if key not in sprite_keys:
            errors.append("%s: آیکن «%s» در اسپرایت نیست." % (relative, key))

# ارجاع‌های #i-KEY در جاوااسکریپت
for js_name in os.listdir(os.path.join(ROOT, "static", "js")):
    if not js_name.endswith(".js"):
        continue
    js_source = read(os.path.join(ROOT, "static", "js", js_name))
    for key in re.findall(r"#i-([\w-]+)", js_source):
        if key not in sprite_keys:
            errors.append("static/js/%s: آیکن «%s» در اسپرایت نیست." % (js_name, key))

# هشدار برای ایموجی‌های جامانده
EMOJI_RANGE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\uFE0F\u2795-\u2797]"
)
for relative in template_files:
    if relative.endswith("_sprite.html"):
        continue
    source = read(os.path.join(TEMPLATES_DIR, relative))
    found = EMOJI_RANGE.findall(source)
    if found:
        warnings.append("%s: ایموجی جامانده %s" % (relative, "".join(sorted(set(found)))))
for js_name in os.listdir(os.path.join(ROOT, "static", "js")):
    if not js_name.endswith(".js"):
        continue
    js_source = read(os.path.join(ROOT, "static", "js", js_name))
    found = EMOJI_RANGE.findall(js_source)
    if found:
        warnings.append("static/js/%s: ایموجی جامانده %s" % (js_name, "".join(sorted(set(found)))))

print("۶) کلاس‌های CSS استفاده‌شده در قالب‌ها")
css_source = read(os.path.join(ROOT, "static", "css", "app.css"))
used_classes = set()
for relative in template_files:
    source = read(os.path.join(TEMPLATES_DIR, relative))
    for match in re.finditer(r'class="([^"{}]+)"', source):
        for token in match.group(1).split():
            if token and not token.startswith("{"):
                used_classes.add(token)
missing = sorted(cls for cls in used_classes if ("." + cls) not in css_source)
if missing:
    warnings.append("کلاس‌های بدون استایل: " + ", ".join(missing))

print()
for warning in warnings:
    print("⚠ " + warning)
if errors:
    print("\nنتیجه: %d خطا" % len(errors))
    for error in errors:
        print("  ✗ " + error)
    sys.exit(1)
print("نتیجه: قالب‌ها و مسیرها سالم هستند ✓")
