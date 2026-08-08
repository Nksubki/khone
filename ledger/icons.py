"""
فهرست آیکن‌های SVG برنامه.

آیکن‌ها در قالب templates/ledger/partials/_sprite.html به‌صورت <symbol id="i-KEY">
تعریف شده‌اند و با تگ {% icon "KEY" %} در قالب‌ها استفاده می‌شوند.
"""

DEFAULT_ICON = "box"

# آیکن‌های رابط کاربری
UI_ICONS = (
    "dashboard", "receipt", "chart", "folder", "building", "users", "clock",
    "gear", "sliders", "plus", "mic", "mic-off", "calendar", "search",
    "download", "pencil", "trash", "check", "x", "chevron-left",
    "chevron-right", "moon", "sun", "menu", "logout", "eye", "eye-off",
    "filter", "info", "wallet", "arrow-down-circle", "arrow-up-circle",
    "image", "phone", "note", "key", "user-plus", "shield", "pin",
    "font-size",
)

# آیکن‌های قابل انتخاب برای دسته‌بندی‌ها (کلید، عنوان فارسی)
CATEGORY_ICON_CHOICES = (
    ("rebar", "میلگرد و آهن"),
    ("cement", "کیسه سیمان"),
    ("brick", "آجر و بلوک"),
    ("sand", "شن و ماسه"),
    ("mixer", "میکسر بتن"),
    ("helmet", "کلاه کارگر"),
    ("trowel", "ماله بنّایی"),
    ("bolt", "برق"),
    ("droplet", "لوله‌کشی و آب"),
    ("tile", "کاشی و سرامیک"),
    ("door", "درب"),
    ("window", "پنجره"),
    ("paint", "رنگ و نقاشی"),
    ("layers", "عایق و ایزوگام"),
    ("crane", "جرثقیل"),
    ("truck", "حمل و نقل"),
    ("columns", "شهرداری و اداری"),
    ("ruler", "نقشه و مهندسی"),
    ("ladder", "نردبان و داربست"),
    ("hammer", "چکش"),
    ("tools", "ابزار"),
    ("tree", "محوطه و فضای سبز"),
    ("sofa", "دکوراسیون"),
    ("lightbulb", "روشنایی"),
    ("building", "ساختمان"),
    ("home", "خانه و واحد"),
    ("bank", "بانک و وام"),
    ("coins", "پول و نقدی"),
    ("wallet", "کیف پول"),
    ("partner", "شریک"),
    ("invoice", "فاکتور"),
    ("receipt", "رسید"),
    ("note", "یادداشت"),
    ("phone", "تلفن و ارتباطات"),
    ("image", "تصویر"),
    ("key", "کلید و تحویل"),
    ("shield", "بیمه و تضمین"),
    ("box", "متفرقه"),
)

CATEGORY_ICONS = tuple(key for key, _label in CATEGORY_ICON_CHOICES)

# همه کلیدهای معتبر
ICON_KEYS = frozenset(UI_ICONS) | frozenset(CATEGORY_ICONS)


def safe_icon(name):
    """کلید آیکن معتبر برمی‌گرداند؛ اگر ناشناخته بود آیکن پیش‌فرض."""
    key = (name or "").strip()
    if key in ICON_KEYS:
        return key
    return DEFAULT_ICON
