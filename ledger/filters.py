"""موتور فیلتر و گزارش‌گیری تراکنش‌ها."""
import datetime

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import KIND_EXPENSE, KIND_INCOME, Category, Project, Transaction
from .utils import jalali
from .utils.numbers import parse_amount

RANGE_CHOICES = (
    ("today", "امروز"),
    ("yesterday", "دیروز"),
    ("week", "این هفته"),
    ("month", "این ماه"),
    ("last_month", "ماه گذشته"),
    ("last30", "۳۰ روز اخیر"),
    ("season", "این فصل"),
    ("year", "امسال"),
    ("last_year", "سال گذشته"),
    ("all", "همه زمان‌ها"),
    ("custom", "بازه دلخواه"),
)

SORT_CHOICES = (
    ("-date", "جدیدترین تاریخ"),
    ("date", "قدیمی‌ترین تاریخ"),
    ("-amount", "بیشترین مبلغ"),
    ("amount", "کمترین مبلغ"),
    ("-created_at", "آخرین ثبت"),
)

VALID_SORTS = {key for key, _ in SORT_CHOICES}


def resolve_range(key, today=None):
    """کلید بازه را به (تاریخ شروع، تاریخ پایان، برچسب) تبدیل می‌کند."""
    today = today or timezone.localdate()
    jy, jm, jd = jalali.to_jalali(today)

    if key == "today":
        return today, today, "امروز"
    if key == "yesterday":
        day = today - datetime.timedelta(days=1)
        return day, day, "دیروز"
    if key == "week":
        start, end = jalali.week_range(today)
        return start, end, "این هفته (شنبه تا جمعه)"
    if key == "month":
        start, end = jalali.jalali_month_range(jy, jm)
        return start, end, "ماه %s" % jalali.format_jalali_month(jy, jm)
    if key == "last_month":
        y, m = jalali.add_jalali_months(jy, jm, -1)
        start, end = jalali.jalali_month_range(y, m)
        return start, end, "ماه %s" % jalali.format_jalali_month(y, m)
    if key == "last30":
        return today - datetime.timedelta(days=29), today, "۳۰ روز اخیر"
    if key == "season":
        season_start_month = ((jm - 1) // 3) * 3 + 1
        start, _ = jalali.jalali_month_range(jy, season_start_month)
        _, end = jalali.jalali_month_range(jy, season_start_month + 2)
        return start, end, "فصل %s %s" % (
            jalali.season_name(jm),
            jalali.to_persian_digits(jy),
        )
    if key == "year":
        start, end = jalali.jalali_year_range(jy)
        return start, end, "سال %s" % jalali.to_persian_digits(jy)
    if key == "last_year":
        start, end = jalali.jalali_year_range(jy - 1)
        return start, end, "سال %s" % jalali.to_persian_digits(jy - 1)
    return None, None, "همه زمان‌ها"


class TransactionFilter:
    """
    خواندن پارامترهای GET و ساخت کوئری‌ست فیلترشده.

    پارامترها:
        q, kind, cat (چندتایی), user (چندتایی), project, method,
        range, from, to, min, max, sort
    """

    def __init__(self, request, queryset=None):
        self.request = request
        self.data = request.GET
        self.user = request.user
        self.errors = []
        self.today = timezone.localdate()

        base = queryset if queryset is not None else Transaction.objects.all()
        self.base_queryset = base.visible_to(request.user)

        self.q = (self.data.get("q") or "").strip()
        self.kind = self.data.get("kind") or ""
        if self.kind not in ("", KIND_EXPENSE, KIND_INCOME):
            self.kind = ""

        self.category_ids = self._int_list("cat")
        self.user_ids = self._int_list("user")
        self.project_id = self._int(self.data.get("project"))
        self.method = self.data.get("method") or ""

        self.range_key = self.data.get("range") or "month"
        valid_ranges = {key for key, _ in RANGE_CHOICES}
        if self.range_key not in valid_ranges:
            self.range_key = "month"

        self.date_from = jalali.parse_jalali_date(self.data.get("from"))
        self.date_to = jalali.parse_jalali_date(self.data.get("to"))
        if self.data.get("from") and self.date_from is None:
            self.errors.append("تاریخ «از» نامعتبر است و نادیده گرفته شد.")
        if self.data.get("to") and self.date_to is None:
            self.errors.append("تاریخ «تا» نامعتبر است و نادیده گرفته شد.")

        if self.date_from or self.date_to:
            self.range_key = "custom"

        if self.range_key == "custom":
            self.start = self.date_from
            self.end = self.date_to
            if self.start and self.end and self.start > self.end:
                self.start, self.end = self.end, self.start
            self.range_label = self._custom_label()
        else:
            self.start, self.end, self.range_label = resolve_range(self.range_key, self.today)

        self.min_amount = parse_amount(self.data.get("min")) if self.data.get("min") else None
        self.max_amount = parse_amount(self.data.get("max")) if self.data.get("max") else None

        self.sort = self.data.get("sort") or "-date"
        if self.sort not in VALID_SORTS:
            self.sort = "-date"

    # ------------------------------------------------------------------ #
    def _int(self, value):
        try:
            return int(jalali.to_english_digits(str(value)))
        except (TypeError, ValueError):
            return None

    def _int_list(self, key):
        result = []
        for raw in self.data.getlist(key):
            for piece in str(raw).split(","):
                value = self._int(piece)
                if value is not None:
                    result.append(value)
        return result

    def _custom_label(self):
        if self.start and self.end:
            return "از %s تا %s" % (
                jalali.format_jalali(self.start),
                jalali.format_jalali(self.end),
            )
        if self.start:
            return "از %s به بعد" % jalali.format_jalali(self.start)
        if self.end:
            return "تا %s" % jalali.format_jalali(self.end)
        return "همه زمان‌ها"

    # ------------------------------------------------------------------ #
    def queryset(self):
        qs = self.base_queryset
        if self.kind:
            qs = qs.filter(kind=self.kind)
        if self.category_ids:
            qs = qs.filter(category_id__in=self.category_ids)
        if self.user_ids:
            qs = qs.filter(created_by_id__in=self.user_ids)
        if self.project_id:
            qs = qs.filter(project_id=self.project_id)
        if self.method:
            qs = qs.filter(payment_method=self.method)
        qs = qs.in_range(self.start, self.end)
        if self.min_amount is not None:
            qs = qs.filter(amount__gte=self.min_amount)
        if self.max_amount is not None:
            qs = qs.filter(amount__lte=self.max_amount)
        if self.q:
            needle = self.q
            qs = qs.filter(
                Q(description__icontains=needle)
                | Q(payee__icontains=needle)
                | Q(category__name__icontains=needle)
                | Q(project__name__icontains=needle)
            )
        return qs.with_relations().order_by(self.sort, "-id")

    # ------------------------------------------------------------------ #
    @property
    def is_filtered(self):
        return bool(
            self.q
            or self.kind
            or self.category_ids
            or self.user_ids
            or self.project_id
            or self.method
            or self.min_amount
            or self.max_amount
            or self.range_key not in ("month",)
        )

    def chips(self):
        """برچسب فیلترهای فعال برای نمایش و حذف تک‌تک."""
        items = []
        items.append({"param": "range", "value": "", "label": "بازه: %s" % self.range_label,
                      "removable": self.range_key != "month"})
        if self.kind:
            label = "هزینه‌ها" if self.kind == KIND_EXPENSE else "دریافتی‌ها"
            items.append({"param": "kind", "value": "", "label": "نوع: %s" % label, "removable": True})
        if self.q:
            items.append({"param": "q", "value": "", "label": "جستجو: %s" % self.q, "removable": True})
        for category in Category.objects.filter(id__in=self.category_ids):
            items.append({"param": "cat", "value": category.id,
                          "label": "دسته: %s" % category.name, "removable": True})
        from django.contrib.auth.models import User

        for user in User.objects.filter(id__in=self.user_ids).select_related("profile"):
            name = getattr(getattr(user, "profile", None), "display_name", user.username)
            items.append({"param": "user", "value": user.id,
                          "label": "کاربر: %s" % name, "removable": True})
        if self.project_id:
            project = Project.objects.filter(id=self.project_id).first()
            if project:
                items.append({"param": "project", "value": "",
                              "label": "پروژه: %s" % project.name, "removable": True})
        if self.min_amount:
            items.append({"param": "min", "value": "",
                          "label": "از مبلغ %s" % jalali.to_persian_digits("{:,}".format(self.min_amount)),
                          "removable": True})
        if self.max_amount:
            items.append({"param": "max", "value": "",
                          "label": "تا مبلغ %s" % jalali.to_persian_digits("{:,}".format(self.max_amount)),
                          "removable": True})
        return items


# --------------------------------------------------------------------------- #
#  جمع‌بندی و گروه‌بندی
# --------------------------------------------------------------------------- #
def summarize(queryset):
    expense = queryset.filter(kind=KIND_EXPENSE).aggregate(
        total=Sum("amount"), count=Count("id")
    )
    income = queryset.filter(kind=KIND_INCOME).aggregate(total=Sum("amount"), count=Count("id"))
    expense_total = expense["total"] or 0
    income_total = income["total"] or 0
    expense_count = expense["count"] or 0
    return {
        "expense_total": expense_total,
        "income_total": income_total,
        "balance": income_total - expense_total,
        "expense_count": expense_count,
        "income_count": income["count"] or 0,
        "count": (expense["count"] or 0) + (income["count"] or 0),
        "average": int(expense_total / expense_count) if expense_count else 0,
    }


def _percent(value, total):
    if not total:
        return 0
    return round(value * 100 / total, 1)


def group_by_category(queryset, kind=KIND_EXPENSE):
    rows = (
        queryset.filter(kind=kind)
        .order_by()
        .values("category__id", "category__name", "category__icon", "category__color")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    grand = sum(r["total"] or 0 for r in rows)
    result = []
    for row in rows:
        total = row["total"] or 0
        result.append(
            {
                "id": row["category__id"],
                "name": row["category__name"],
                "icon": row["category__icon"] or "",
                "color": row["category__color"] or "#3b82f6",
                "total": total,
                "count": row["count"],
                "percent": _percent(total, grand),
            }
        )
    return result, grand


def group_by_user(queryset, kind=KIND_EXPENSE):
    rows = (
        queryset.filter(kind=kind)
        .order_by()
        .values(
            "created_by__id",
            "created_by__username",
            "created_by__profile__full_name",
            "created_by__first_name",
            "created_by__last_name",
        )
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    grand = sum(r["total"] or 0 for r in rows)
    result = []
    palette = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ec4899", "#14b8a6", "#ef4444"]
    for index, row in enumerate(rows):
        name = (row["created_by__profile__full_name"] or "").strip()
        if not name:
            name = ("%s %s" % (row["created_by__first_name"] or "", row["created_by__last_name"] or "")).strip()
        if not name:
            name = row["created_by__username"]
        total = row["total"] or 0
        result.append(
            {
                "id": row["created_by__id"],
                "name": name,
                "username": row["created_by__username"],
                "total": total,
                "count": row["count"],
                "percent": _percent(total, grand),
                "color": palette[index % len(palette)],
            }
        )
    return result, grand


def group_by_project(queryset, kind=KIND_EXPENSE):
    rows = (
        queryset.filter(kind=kind)
        .order_by()
        .values("project__id", "project__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    grand = sum(r["total"] or 0 for r in rows)
    result = []
    for row in rows:
        total = row["total"] or 0
        result.append(
            {
                "id": row["project__id"],
                "name": row["project__name"] or "بدون پروژه",
                "total": total,
                "count": row["count"],
                "percent": _percent(total, grand),
                "color": "#6366f1",
            }
        )
    return result, grand


def group_by_payment(queryset, kind=KIND_EXPENSE):
    from .models import PAYMENT_CHOICES

    labels = dict(PAYMENT_CHOICES)
    rows = (
        queryset.filter(kind=kind)
        .order_by()
        .values("payment_method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    rows = list(rows)
    grand = sum(r["total"] or 0 for r in rows)
    return [
        {
            "name": labels.get(row["payment_method"], row["payment_method"]),
            "total": row["total"] or 0,
            "count": row["count"],
            "percent": _percent(row["total"] or 0, grand),
            "color": "#0ea5e9",
        }
        for row in rows
    ], grand


def group_by_month(queryset, kind=KIND_EXPENSE, months=None):
    """
    جمع هزینه به تفکیک ماه شمسی.
    اگر months (فهرست خروجی jalali.last_jalali_months) داده شود،
    ماه‌های خالی هم با مقدار صفر برگردانده می‌شوند.
    """
    buckets = {}
    for date_value, amount in queryset.filter(kind=kind).values_list("date", "amount"):
        jy, jm, _ = jalali.to_jalali(date_value)
        buckets[(jy, jm)] = buckets.get((jy, jm), 0) + (amount or 0)

    if months:
        keys = [(jy, jm) for jy, jm, _s, _e in months]
    else:
        keys = sorted(buckets.keys())

    grand = max(buckets.values()) if buckets else 0
    return [
        {
            "year": jy,
            "month": jm,
            "label": jalali.month_name(jm),
            "full_label": jalali.format_jalali_month(jy, jm),
            "total": buckets.get((jy, jm), 0),
            "percent": _percent(buckets.get((jy, jm), 0), grand),
        }
        for jy, jm in keys
    ]


def group_by_day(queryset, kind=KIND_EXPENSE, days=14, today=None):
    """جمع روزانه برای نمودار خطی/میله‌ای کوتاه‌مدت."""
    today = today or timezone.localdate()
    start = today - datetime.timedelta(days=days - 1)
    buckets = {}
    for date_value, amount in (
        queryset.filter(kind=kind, date__gte=start, date__lte=today)
        .values_list("date", "amount")
    ):
        buckets[date_value] = buckets.get(date_value, 0) + (amount or 0)
    peak = max(buckets.values()) if buckets else 0
    result = []
    for i in range(days):
        day = start + datetime.timedelta(days=i)
        total = buckets.get(day, 0)
        result.append(
            {
                "date": day,
                "label": jalali.to_persian_digits(jalali.to_jalali(day)[2]),
                "full_label": jalali.format_jalali_long(day),
                "total": total,
                "percent": _percent(total, peak),
            }
        )
    return result
