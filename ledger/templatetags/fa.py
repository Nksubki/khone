"""فیلترها و تگ‌های قالب برای نمایش فارسی (تاریخ شمسی، مبلغ، ارقام) و آیکن‌های SVG."""
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from ..icons import safe_icon
from ..utils import jalali
from ..utils.numbers import format_money, group_digits, humanize_amount

register = template.Library()


# --------------------------------------------------------------------------- #
#  آیکن‌های SVG (به‌جای ایموجی)
# --------------------------------------------------------------------------- #
@register.simple_tag(name="icon")
def icon_tag(name, css="", title=""):
    """
    درج آیکن SVG از اسپرایت صفحه.

    نمونه‌ها:
        {% icon "mic" %}
        {% icon "trash" "icon-lg" %}
        {% icon category.icon "" category.name %}
    """
    key = safe_icon(name)
    classes = ("icon " + (css or "")).strip()
    label = (title or "").strip()
    if label:
        markup = (
            '<svg class="%s" role="img" aria-label="%s"><title>%s</title>'
            '<use href="#i-%s"></use></svg>'
        ) % (escape(classes), escape(label), escape(label), key)
    else:
        markup = (
            '<svg class="%s" aria-hidden="true" focusable="false">'
            '<use href="#i-%s"></use></svg>'
        ) % (escape(classes), key)
    return mark_safe(markup)


@register.filter(name="icon_key")
def icon_key(name):
    """کلید آیکن معتبر (برای استفاده در ویژگی‌های HTML)."""
    return safe_icon(name)


# --------------------------------------------------------------------------- #
#  ارقام و مبالغ
# --------------------------------------------------------------------------- #
@register.filter(name="fa")
def fa_digits(value):
    """ارقام لاتین را فارسی می‌کند."""
    return jalali.to_persian_digits(value)


@register.filter(name="money")
def money(value):
    """۱۲۳۴۵۶۷ → ۱,۲۳۴,۵۶۷"""
    return format_money(value)


@register.filter(name="toman")
def toman(value):
    """۱۲۳۴۵۶۷ → ۱,۲۳۴,۵۶۷ تومان"""
    text = format_money(value)
    if not text:
        return ""
    return mark_safe("%s <span class=\"unit\">تومان</span>" % text)


@register.filter(name="money_plain")
def money_plain(value):
    return group_digits(value)


@register.filter(name="amount_words")
def amount_words(value):
    """۲۳۰۵۰۰۰۰۰ → «۲۳۰ میلیون و ۵۰۰ هزار»"""
    return humanize_amount(value)


@register.filter(name="short_money")
def short_money(value):
    """نمایش خیلی فشرده برای کارت‌های آماری: ۲.۳ میلیارد"""
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return ""
    negative = number < 0
    number = abs(number)
    for scale, label in (
        (1_000_000_000_000, "همت"),
        (1_000_000_000, "میلیارد"),
        (1_000_000, "میلیون"),
        (1_000, "هزار"),
    ):
        if number >= scale:
            value2 = number / scale
            text = ("%.1f" % value2).rstrip("0").rstrip(".")
            out = "%s %s" % (text, label)
            return jalali.to_persian_digits(("منفی " if negative else "") + out)
    return jalali.to_persian_digits(("-" if negative else "") + str(number))


# --------------------------------------------------------------------------- #
#  تاریخ شمسی
# --------------------------------------------------------------------------- #
@register.filter(name="jdate")
def jdate(value):
    return jalali.format_jalali(value)


@register.filter(name="jdate_long")
def jdate_long(value):
    return jalali.format_jalali_long(value)


@register.filter(name="jdate_full")
def jdate_full(value):
    return jalali.format_jalali_full(value)


@register.filter(name="jdatetime")
def jdatetime(value):
    """تاریخ و ساعت (به وقت تهران) برای فیلدهای DateTimeField."""
    if not value:
        return ""
    from django.utils import timezone

    try:
        local = timezone.localtime(value)
    except (ValueError, TypeError):
        local = value
    date_part = jalali.format_jalali_long(local)
    time_part = jalali.to_persian_digits(local.strftime("%H:%M"))
    return "%s ساعت %s" % (date_part, time_part)


@register.filter(name="jtime")
def jtime(value):
    if not value:
        return ""
    return jalali.to_persian_digits(value.strftime("%H:%M"))


# --------------------------------------------------------------------------- #
#  کار با پارامترهای آدرس (فیلترها)
# --------------------------------------------------------------------------- #
def _params(context):
    request = context.get("request")
    if request is None:
        from django.http import QueryDict

        return QueryDict("", mutable=True)
    return request.GET.copy()


def _render(params):
    encoded = params.urlencode()
    return "?" + encoded if encoded else "?"


@register.simple_tag(takes_context=True)
def url_with(context, **kwargs):
    """آدرس فعلی با تغییر/افزودن پارامترهای داده‌شده (صفحه‌بندی ریست می‌شود)."""
    params = _params(context)
    for key, value in kwargs.items():
        if value in (None, "", "None"):
            params.pop(key, None)
        else:
            params.setlist(key, [str(value)])
    if "page" not in kwargs:
        params.pop("page", None)
    return _render(params)


@register.simple_tag(takes_context=True)
def url_page(context, page):
    params = _params(context)
    params.setlist("page", [str(page)])
    return _render(params)


@register.simple_tag(takes_context=True)
def url_remove(context, key, value=None):
    """حذف کامل یک پارامتر یا حذف یک مقدار از پارامتر چندمقداری."""
    params = _params(context)
    if value in (None, ""):
        params.pop(key, None)
    else:
        remaining = [v for v in params.getlist(key) if str(v) != str(value)]
        if remaining:
            params.setlist(key, remaining)
        else:
            params.pop(key, None)
    params.pop("page", None)
    return _render(params)


@register.simple_tag(takes_context=True)
def url_toggle(context, key, value):
    """افزودن/برداشتن یک مقدار از پارامتر چندمقداری (برای فیلتر دسته‌ها)."""
    params = _params(context)
    values = [str(v) for v in params.getlist(key)]
    text = str(value)
    if text in values:
        values.remove(text)
    else:
        values.append(text)
    if values:
        params.setlist(key, values)
    else:
        params.pop(key, None)
    params.pop("page", None)
    return _render(params)


@register.simple_tag(takes_context=True)
def url_sort(context, value):
    return url_with(context, sort=value)


# --------------------------------------------------------------------------- #
#  کمک‌های نمایشی
# --------------------------------------------------------------------------- #
@register.filter(name="percent")
def percent(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return ""
    text = ("%.1f" % number).rstrip("0").rstrip(".")
    return jalali.to_persian_digits(text) + "٪"


@register.filter(name="bar_width")
def bar_width(value):
    """درصد را برای style عرض میله برمی‌گرداند (با ارقام لاتین)."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    number = max(0.0, min(100.0, number))
    return ("%.2f" % number).rstrip("0").rstrip(".") or "0"


@register.filter(name="field_class")
def field_class(field, css):
    """افزودن کلاس به ویجت یک فیلد فرم."""
    attrs = field.field.widget.attrs
    existing = attrs.get("class", "")
    attrs["class"] = (existing + " " + css).strip()
    return field


@register.simple_tag
def initials(name):
    text = (name or "").strip()
    if not text:
        return "؟"
    parts = text.split()
    if len(parts) == 1:
        return parts[0][:1]
    return parts[0][:1] + parts[1][:1]
