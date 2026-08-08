"""مدل‌های داده برنامه حسابداری ساختمان."""
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .utils import jalali
from .utils.numbers import format_money, humanize_amount

ROLE_OWNER = "owner"
ROLE_PARTNER = "partner"
ROLE_VIEWER = "viewer"

ROLE_CHOICES = (
    (ROLE_OWNER, "مدیر (دسترسی کامل)"),
    (ROLE_PARTNER, "شریک (ثبت و مشاهده)"),
    (ROLE_VIEWER, "ناظر (فقط مشاهده)"),
)

KIND_EXPENSE = "expense"
KIND_INCOME = "income"

KIND_CHOICES = (
    (KIND_EXPENSE, "هزینه"),
    (KIND_INCOME, "دریافت / واریز"),
)

PAYMENT_CHOICES = (
    ("cash", "نقدی"),
    ("card", "کارت به کارت"),
    ("transfer", "حواله / پایا"),
    ("cheque", "چک"),
    ("credit", "نسیه / بدهی"),
    ("other", "سایر"),
)

COLOR_CHOICES = (
    ("#ef4444", "قرمز"),
    ("#f97316", "نارنجی"),
    ("#f59e0b", "کهربایی"),
    ("#eab308", "زرد"),
    ("#84cc16", "لیمویی"),
    ("#22c55e", "سبز"),
    ("#10b981", "زمرد"),
    ("#14b8a6", "فیروزه‌ای"),
    ("#06b6d4", "آبی روشن"),
    ("#3b82f6", "آبی"),
    ("#6366f1", "بنفش آبی"),
    ("#8b5cf6", "بنفش"),
    ("#a855f7", "ارغوانی"),
    ("#ec4899", "صورتی"),
    ("#78716c", "خاکی"),
    ("#64748b", "طوسی"),
)


class Profile(models.Model):
    """اطلاعات تکمیلی و نقش هر کاربر."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="کاربر"
    )
    full_name = models.CharField("نام و نام خانوادگی", max_length=150, blank=True)
    phone = models.CharField("شماره تماس", max_length=20, blank=True)
    role = models.CharField("نقش", max_length=20, choices=ROLE_CHOICES, default=ROLE_PARTNER)
    can_view_all = models.BooleanField(
        "دیدن هزینه‌های سایر کاربران", default=True,
    )
    note = models.CharField("یادداشت", max_length=255, blank=True)
    created_at = models.DateTimeField("تاریخ ساخت", auto_now_add=True)

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل کاربران"

    def __str__(self):
        return self.display_name

    # ------------------------------------------------------------------ #
    @property
    def display_name(self):
        return self.full_name.strip() or self.user.get_full_name().strip() or self.user.username

    @property
    def initials(self):
        name = self.display_name.strip()
        if not name:
            return "؟"
        parts = name.split()
        if len(parts) == 1:
            return parts[0][:1]
        return parts[0][:1] + parts[1][:1]

    @property
    def is_owner(self):
        return self.role == ROLE_OWNER or self.user.is_superuser

    @property
    def is_viewer(self):
        return self.role == ROLE_VIEWER and not self.user.is_superuser

    @property
    def can_add_records(self):
        return not self.is_viewer

    @property
    def can_manage_users(self):
        return self.is_owner

    @property
    def can_manage_categories(self):
        """شریک‌ها هم می‌توانند دسته‌بندی اضافه کنند."""
        return not self.is_viewer

    @property
    def can_delete_categories(self):
        return self.is_owner

    @property
    def sees_everything(self):
        return self.is_owner or self.can_view_all


def get_profile(user):
    """پروفایل کاربر را برمی‌گرداند و اگر نبود می‌سازد."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.profile
    except Profile.DoesNotExist:
        return Profile.objects.create(
            user=user,
            role=ROLE_OWNER if user.is_superuser else ROLE_PARTNER,
            full_name=user.get_full_name(),
        )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "role": ROLE_OWNER if instance.is_superuser else ROLE_PARTNER,
                "full_name": instance.get_full_name(),
            },
        )


class Project(models.Model):
    """پروژه یا ساختمان (اختیاری — برای تفکیک چند کارگاه)."""

    name = models.CharField("نام پروژه", max_length=120, unique=True)
    address = models.CharField("آدرس", max_length=255, blank=True)
    description = models.TextField("توضیحات", blank=True)
    budget = models.BigIntegerField("بودجه پیش‌بینی‌شده (تومان)", null=True, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
        verbose_name="ایجادکننده",
    )
    created_at = models.DateTimeField("تاریخ ساخت", auto_now_add=True)

    class Meta:
        verbose_name = "پروژه"
        verbose_name_plural = "پروژه‌ها"
        ordering = ("-is_active", "name")

    def __str__(self):
        return self.name

    def total_expense(self):
        return (
            self.transactions.filter(kind=KIND_EXPENSE).aggregate(s=models.Sum("amount"))["s"] or 0
        )

    def total_income(self):
        return (
            self.transactions.filter(kind=KIND_INCOME).aggregate(s=models.Sum("amount"))["s"] or 0
        )

    @property
    def budget_percent(self):
        if not self.budget:
            return None
        return min(100, round(self.total_expense() * 100 / self.budget))


class Category(models.Model):
    """دسته‌بندی هزینه — مثل میلگرد و آهن، سیمان، دستمزد بنّا و ..."""

    name = models.CharField("نام دسته‌بندی", max_length=120, unique=True)
    kind = models.CharField(
        "نوع", max_length=20, choices=KIND_CHOICES, default=KIND_EXPENSE
    )
    icon = models.CharField("آیکن (ایموجی)", max_length=8, blank=True, default="🧱")
    color = models.CharField(
        "رنگ", max_length=9, choices=COLOR_CHOICES, default="#3b82f6"
    )
    description = models.CharField("توضیح کوتاه", max_length=255, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.IntegerField("ترتیب نمایش", default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_categories",
        verbose_name="ایجادکننده",
    )
    created_at = models.DateTimeField("تاریخ ساخت", auto_now_add=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    @property
    def label(self):
        return ("%s %s" % (self.icon, self.name)).strip()

    def total(self, kind=KIND_EXPENSE):
        return self.transactions.filter(kind=kind).aggregate(s=models.Sum("amount"))["s"] or 0

    @property
    def transaction_count(self):
        return self.transactions.count()


class TransactionQuerySet(models.QuerySet):
    def expenses(self):
        return self.filter(kind=KIND_EXPENSE)

    def incomes(self):
        return self.filter(kind=KIND_INCOME)

    def in_range(self, start=None, end=None):
        qs = self
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def visible_to(self, user):
        """اگر کاربر اجازه دیدن همه را نداشته باشد فقط رکوردهای خودش."""
        profile = get_profile(user)
        if profile and profile.sees_everything:
            return self
        return self.filter(created_by=user)

    def total(self):
        return self.aggregate(s=models.Sum("amount"))["s"] or 0

    def with_relations(self):
        return self.select_related("category", "project", "created_by", "created_by__profile")


class Transaction(models.Model):
    """یک رکورد هزینه یا دریافت."""

    kind = models.CharField("نوع", max_length=20, choices=KIND_CHOICES, default=KIND_EXPENSE)
    amount = models.BigIntegerField("مبلغ (تومان)")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="دسته‌بندی",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="پروژه",
    )
    description = models.TextField("توضیحات", blank=True)
    date = models.DateField("تاریخ", default=timezone.localdate)
    time = models.TimeField("ساعت", null=True, blank=True)
    payee = models.CharField("طرف حساب / فروشنده", max_length=150, blank=True)
    payment_method = models.CharField(
        "نحوه پرداخت", max_length=20, choices=PAYMENT_CHOICES, default="cash"
    )
    receipt = models.FileField(
        "تصویر فاکتور / رسید", upload_to="receipts/%Y/%m", null=True, blank=True
    )
    voice_used = models.BooleanField("ثبت با صدا", default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="ثبت‌کننده",
    )
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    objects = TransactionQuerySet.as_manager()

    class Meta:
        verbose_name = "تراکنش"
        verbose_name_plural = "تراکنش‌ها"
        ordering = ("-date", "-time", "-id")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["kind", "date"]),
            models.Index(fields=["category", "date"]),
            models.Index(fields=["created_by", "date"]),
        ]

    def __str__(self):
        return "%s — %s تومان" % (self.category.name if self.category_id else "?", format_money(self.amount, persian=False))

    # ------------------------------------------------------------------ #
    #  نمایش
    # ------------------------------------------------------------------ #
    @property
    def is_expense(self):
        return self.kind == KIND_EXPENSE

    @property
    def signed_amount(self):
        return self.amount if self.kind == KIND_INCOME else -self.amount

    @property
    def jalali_date(self):
        return jalali.format_jalali(self.date)

    @property
    def jalali_date_long(self):
        return jalali.format_jalali_long(self.date)

    @property
    def jalali_date_full(self):
        return jalali.format_jalali_full(self.date)

    @property
    def jalali_date_input(self):
        """قالب مناسب فیلد ورودی: 1405/05/17 با ارقام لاتین."""
        return jalali.format_jalali(self.date, persian_digits=False)

    @property
    def time_display(self):
        if not self.time:
            return ""
        return jalali.to_persian_digits(self.time.strftime("%H:%M"))

    @property
    def amount_display(self):
        return format_money(self.amount)

    @property
    def amount_words(self):
        return humanize_amount(self.amount)

    @property
    def short_description(self):
        text = (self.description or "").strip()
        if len(text) <= 90:
            return text
        return text[:90] + "…"

    def can_edit(self, user):
        profile = get_profile(user)
        if not profile or profile.is_viewer:
            return False
        return profile.is_owner or self.created_by_id == user.id

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("ledger:transaction_detail", args=[self.pk])


class ActivityLog(models.Model):
    """گزارش فعالیت‌ها برای شفافیت بین شرکا."""

    ACTIONS = (
        ("create", "ثبت"),
        ("update", "ویرایش"),
        ("delete", "حذف"),
        ("login", "ورود"),
        ("user", "مدیریت کاربر"),
        ("category", "دسته‌بندی"),
        ("project", "پروژه"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
        verbose_name="کاربر",
    )
    action = models.CharField("عملیات", max_length=20, choices=ACTIONS)
    summary = models.CharField("شرح", max_length=255)
    created_at = models.DateTimeField("زمان", auto_now_add=True)

    class Meta:
        verbose_name = "فعالیت"
        verbose_name_plural = "گزارش فعالیت‌ها"
        ordering = ("-created_at",)

    def __str__(self):
        return "%s — %s" % (self.get_action_display(), self.summary)

    @property
    def jalali_datetime(self):
        local = timezone.localtime(self.created_at)
        return "%s — %s" % (
            jalali.format_jalali_long(local.date()),
            jalali.to_persian_digits(local.strftime("%H:%M")),
        )


def log_activity(user, action, summary):
    """ثبت یک رویداد در گزارش فعالیت (بی‌صدا در صورت خطا)."""
    try:
        ActivityLog.objects.create(user=user if getattr(user, "is_authenticated", False) else None,
                                   action=action, summary=summary[:255])
    except Exception:  # pragma: no cover - نباید جلوی کار اصلی را بگیرد
        pass


DEFAULT_CATEGORIES = (
    ("میلگرد و آهن", "🏗️", "#ef4444"),
    ("سیمان و گچ", "🪣", "#78716c"),
    ("آجر و بلوک", "🧱", "#f97316"),
    ("شن و ماسه", "⛰️", "#eab308"),
    ("بتن و بتن‌ریزی", "🚧", "#64748b"),
    ("دستمزد کارگر", "👷", "#22c55e"),
    ("دستمزد بنّا", "🧰", "#10b981"),
    ("تأسیسات برقی", "💡", "#f59e0b"),
    ("تأسیسات مکانیکی و لوله‌کشی", "🚰", "#06b6d4"),
    ("کاشی و سرامیک", "🔲", "#8b5cf6"),
    ("درب و پنجره", "🚪", "#a855f7"),
    ("نقاشی و رنگ", "🎨", "#ec4899"),
    ("عایق و ایزوگام", "🛡️", "#3b82f6"),
    ("اجاره ماشین و جرثقیل", "🚜", "#14b8a6"),
    ("حمل و نقل", "🚚", "#6366f1"),
    ("عوارض و شهرداری", "🏛️", "#84cc16"),
    ("مهندس و نقشه‌کشی", "📐", "#0ea5e9"),
    ("متفرقه", "📦", "#64748b"),
)

DEFAULT_INCOME_CATEGORIES = (
    ("آورده شریک", "🤝", "#22c55e"),
    ("فروش واحد", "🏠", "#10b981"),
    ("وام و تسهیلات", "🏦", "#3b82f6"),
    ("سایر دریافتی‌ها", "💰", "#f59e0b"),
)


def create_default_categories(user=None):
    """ساخت دسته‌بندی‌های پیش‌فرض (اگر وجود نداشته باشند)."""
    created = 0
    order = 0
    for name, icon, color in DEFAULT_CATEGORIES:
        order += 10
        _, made = Category.objects.get_or_create(
            name=name,
            defaults={
                "icon": icon,
                "color": color,
                "kind": KIND_EXPENSE,
                "sort_order": order,
                "created_by": user,
            },
        )
        created += 1 if made else 0
    for name, icon, color in DEFAULT_INCOME_CATEGORIES:
        order += 10
        _, made = Category.objects.get_or_create(
            name=name,
            defaults={
                "icon": icon,
                "color": color,
                "kind": KIND_INCOME,
                "sort_order": order,
                "created_by": user,
            },
        )
        created += 1 if made else 0
    return created


MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
