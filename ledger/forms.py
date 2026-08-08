"""فرم‌های برنامه — با پشتیبانی کامل از تاریخ شمسی و اعداد فارسی."""
import datetime
import os
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    KIND_CHOICES,
    KIND_EXPENSE,
    MAX_UPLOAD_SIZE,
    PAYMENT_CHOICES,
    ROLE_CHOICES,
    Category,
    Profile,
    Project,
    Transaction,
)
from .utils import jalali
from .utils.numbers import parse_amount

ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
ALLOWED_RECEIPT_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".pdf"}


# --------------------------------------------------------------------------- #
#  ویجت‌ها و فیلدهای سفارشی
# --------------------------------------------------------------------------- #
class JalaliDateInput(forms.TextInput):
    """ورودی متنی تاریخ شمسی که با تقویم جاوااسکریپتی همراه است."""

    def __init__(self, attrs=None):
        defaults = {
            "class": "field-input jalali-date",
            "placeholder": "۱۴۰۵/۰۵/۱۷",
            "autocomplete": "off",
            "inputmode": "numeric",
            "data-jalali-date": "1",
        }
        if attrs:
            defaults.update(attrs)
        super().__init__(defaults)

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, datetime.datetime):
            value = value.date()
        if isinstance(value, datetime.date):
            return jalali.format_jalali(value, persian_digits=False)
        text = jalali.to_english_digits(str(value))
        match = ISO_DATE_RE.match(text)
        if match:
            gy, gm, gd = (int(g) for g in match.groups())
            jy, jm, jd = jalali.gregorian_to_jalali(gy, gm, gd)
            return "%04d/%02d/%02d" % (jy, jm, jd)
        return text


class JalaliDateField(forms.Field):
    widget = JalaliDateInput
    default_error_messages = {
        "invalid": "تاریخ را به شکل ۱۴۰۵/۰۵/۱۷ وارد کنید.",
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        text = jalali.to_english_digits(str(value)).strip()
        match = ISO_DATE_RE.match(text)
        if match:
            try:
                return datetime.date(*(int(g) for g in match.groups()))
            except ValueError:
                raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        parsed = jalali.parse_jalali_date(text)
        if parsed is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return parsed


class PersianTimeInput(forms.TextInput):
    def __init__(self, attrs=None):
        defaults = {
            "class": "field-input",
            "placeholder": "۱۴:۳۰",
            "autocomplete": "off",
            "inputmode": "numeric",
            "data-time-mask": "1",
        }
        if attrs:
            defaults.update(attrs)
        super().__init__(defaults)

    def format_value(self, value):
        if value in (None, ""):
            return ""
        if isinstance(value, datetime.time):
            return value.strftime("%H:%M")
        return jalali.to_english_digits(str(value))[:5]


class PersianTimeField(forms.Field):
    widget = PersianTimeInput
    default_error_messages = {"invalid": "ساعت را به شکل ۱۴:۳۰ وارد کنید."}

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.time):
            return value
        parsed = jalali.parse_time(value)
        if parsed is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return parsed


class AmountInput(forms.TextInput):
    def __init__(self, attrs=None):
        defaults = {
            "class": "field-input amount-input",
            "placeholder": "مثلاً ۱۰۰,۰۰۰,۰۰۰",
            "autocomplete": "off",
            "inputmode": "decimal",
            "data-amount": "1",
            "dir": "ltr",
        }
        if attrs:
            defaults.update(attrs)
        super().__init__(defaults)

    def format_value(self, value):
        if value in (None, ""):
            return ""
        try:
            return "{:,}".format(int(jalali.to_english_digits(str(value)).replace(",", "")))
        except (TypeError, ValueError):
            return str(value)


class AmountField(forms.Field):
    """مبلغ را از رقم، ارقام فارسی، یا حروف فارسی («صد میلیون») می‌خواند."""

    widget = AmountInput
    default_error_messages = {
        "invalid": "مبلغ را به رقم یا با حروف (مثل «صد میلیون») وارد کنید.",
        "too_small": "مبلغ باید بزرگ‌تر از صفر باشد.",
    }

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, int):
            return value
        parsed = parse_amount(value)
        if parsed is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        if parsed <= 0:
            raise forms.ValidationError(self.error_messages["too_small"], code="too_small")
        return parsed


class CategorySelect(forms.Select):
    """در گزینه‌ها نوع و رنگ دسته را نگه می‌دارد تا جاوااسکریپت فیلتر کند."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-kind"] = instance.kind
            option["attrs"]["data-color"] = instance.color
        return option


class CategoryChoiceField(forms.ModelChoiceField):
    widget = CategorySelect

    def label_from_instance(self, obj):
        return obj.label


# --------------------------------------------------------------------------- #
#  فرم تراکنش
# --------------------------------------------------------------------------- #
class TransactionForm(forms.ModelForm):
    kind = forms.ChoiceField(
        label="نوع رکورد",
        choices=KIND_CHOICES,
        initial=KIND_EXPENSE,
        widget=forms.RadioSelect(attrs={"class": "kind-radio"}),
    )
    amount = AmountField(label="مبلغ (تومان)")
    date = JalaliDateField(label="تاریخ (شمسی)")
    time = PersianTimeField(label="ساعت", required=False)

    class Meta:
        model = Transaction
        fields = (
            "kind",
            "amount",
            "category",
            "project",
            "date",
            "time",
            "description",
            "payee",
            "payment_method",
            "receipt",
        )
        field_classes = {"category": CategoryChoiceField}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "class": "field-input",
                    "rows": 4,
                    "placeholder": "توضیحات… (می‌توانید با میکروفون بگویید)",
                    "data-voice-target": "description",
                }
            ),
            "payee": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "مثلاً آهن‌فروشی رضایی"}
            ),
            "payment_method": forms.Select(attrs={"class": "field-input"}),
            "project": forms.Select(attrs={"class": "field-input"}),
            "receipt": forms.ClearableFileInput(
                attrs={"class": "field-file", "accept": "image/*,.pdf"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )
        self.fields["category"].empty_label = "— انتخاب دسته‌بندی —"
        self.fields["project"].queryset = Project.objects.filter(is_active=True)
        self.fields["project"].empty_label = "— بدون پروژه —"
        self.fields["project"].required = False
        self.fields["payment_method"].choices = PAYMENT_CHOICES
        self.fields["description"].required = False
        self.fields["payee"].required = False

        if not self.instance.pk:
            now = timezone.localtime()
            self.fields["date"].initial = now.date()
            self.fields["time"].initial = now.time().replace(second=0, microsecond=0)

    def clean_receipt(self):
        file = self.cleaned_data.get("receipt")
        if not file:
            return file
        size = getattr(file, "size", 0)
        if size and size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("حجم فایل باید کمتر از ۱۰ مگابایت باشد.")
        name = getattr(file, "name", "") or ""
        ext = os.path.splitext(name)[1].lower()
        if ext and ext not in ALLOWED_RECEIPT_EXT:
            raise forms.ValidationError("فقط تصویر یا فایل PDF مجاز است.")
        return file

    def clean_date(self):
        date = self.cleaned_data.get("date")
        if date and date > timezone.localdate() + datetime.timedelta(days=366 * 2):
            raise forms.ValidationError("تاریخ خیلی دور در آینده است.")
        return date


# --------------------------------------------------------------------------- #
#  دسته‌بندی و پروژه
# --------------------------------------------------------------------------- #
EMOJI_SUGGESTIONS = [
    "🧱", "🏗️", "🪣", "⛰️", "🚧", "👷", "🧰", "💡", "🚰", "🔲",
    "🚪", "🎨", "🛡️", "🚜", "🚚", "🏛️", "📐", "📦", "🤝", "🏠",
    "🏦", "💰", "🪟", "🪜", "🔨", "🪛", "🧯", "🌳", "🛋️", "🧾",
]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "kind", "icon", "color", "description", "sort_order", "is_active")
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "field-input",
                    "placeholder": "مثلاً میلگرد و آهن",
                    "data-voice-target": "name",
                }
            ),
            "kind": forms.RadioSelect(attrs={"class": "kind-radio"}),
            "icon": forms.TextInput(
                attrs={"class": "field-input icon-input", "maxlength": 8, "placeholder": "🧱"}
            ),
            "color": forms.Select(attrs={"class": "field-input color-select"}),
            "description": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "توضیح اختیاری"}
            ),
            "sort_order": forms.NumberInput(attrs={"class": "field-input", "dir": "ltr"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
        self.fields["icon"].required = False
        self.emoji_suggestions = EMOJI_SUGGESTIONS

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("نام دسته‌بندی را بنویسید.")
        qs = Category.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("دسته‌بندی با این نام قبلاً ساخته شده است.")
        return name

    def clean_icon(self):
        return (self.cleaned_data.get("icon") or "").strip() or "🧱"


class ProjectForm(forms.ModelForm):
    budget = AmountField(label="بودجه پیش‌بینی‌شده (تومان)", required=False)

    class Meta:
        model = Project
        fields = ("name", "address", "budget", "description", "is_active")
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "مثلاً پروژه خیابان گلستان"}
            ),
            "address": forms.TextInput(attrs={"class": "field-input", "placeholder": "آدرس"}),
            "description": forms.Textarea(
                attrs={"class": "field-input", "rows": 3, "placeholder": "توضیحات"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].required = False
        self.fields["description"].required = False


# --------------------------------------------------------------------------- #
#  کاربران
# --------------------------------------------------------------------------- #
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.@+-]{3,30}$")


class PartnerCreateForm(forms.Form):
    """ساخت حساب کاربری برای شریک — توسط مدیر."""

    full_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "field-input", "placeholder": "مثلاً حسین رضایی"}
        ),
    )
    username = forms.CharField(
        label="نام کاربری (برای ورود)",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "dir": "ltr",
                "placeholder": "hossein",
                "autocapitalize": "none",
                "autocomplete": "off",
            }
        ),
    )
    phone = forms.CharField(
        label="شماره تماس",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "field-input", "dir": "ltr", "placeholder": "09120000000"}
        ),
    )
    role = forms.ChoiceField(
        label="نقش",
        choices=ROLE_CHOICES,
        initial="partner",
        widget=forms.Select(attrs={"class": "field-input"}),
    )
    can_view_all = forms.BooleanField(
        label="بتواند هزینه‌های ثبت‌شده توسط سایر کاربران را ببیند",
        required=False,
        initial=True,
    )
    password1 = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(
            attrs={"class": "field-input", "dir": "ltr", "autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        widget=forms.PasswordInput(
            attrs={"class": "field-input", "dir": "ltr", "autocomplete": "new-password"}
        ),
    )
    note = forms.CharField(
        label="یادداشت",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "field-input", "placeholder": "اختیاری"}),
    )

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not USERNAME_RE.match(username):
            raise forms.ValidationError(
                "نام کاربری باید ۳ تا ۳۰ نویسه انگلیسی، عدد یا _ باشد."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("این نام کاربری قبلاً استفاده شده است.")
        return username

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        if p2 and len(p2) < 6:
            raise forms.ValidationError("رمز عبور باید حداقل ۶ نویسه باشد.")
        return p2

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            password=data["password1"],
        )
        parts = data["full_name"].strip().split(" ", 1)
        user.first_name = parts[0][:150]
        user.last_name = (parts[1] if len(parts) > 1 else "")[:150]
        user.save(update_fields=["first_name", "last_name"])

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.full_name = data["full_name"].strip()
        profile.phone = data.get("phone", "")
        profile.role = data["role"]
        profile.can_view_all = bool(data.get("can_view_all"))
        profile.note = data.get("note", "")
        profile.save()
        return user


class PartnerEditForm(forms.Form):
    full_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "field-input"}),
    )
    phone = forms.CharField(
        label="شماره تماس",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "field-input", "dir": "ltr"}),
    )
    role = forms.ChoiceField(
        label="نقش", choices=ROLE_CHOICES, widget=forms.Select(attrs={"class": "field-input"})
    )
    can_view_all = forms.BooleanField(
        label="بتواند هزینه‌های سایر کاربران را ببیند", required=False
    )
    is_active = forms.BooleanField(label="حساب فعال باشد", required=False)
    note = forms.CharField(
        label="یادداشت",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"class": "field-input"}),
    )


class ResetPasswordForm(forms.Form):
    password1 = forms.CharField(
        label="رمز عبور جدید",
        widget=forms.PasswordInput(attrs={"class": "field-input", "dir": "ltr"}),
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور جدید",
        widget=forms.PasswordInput(attrs={"class": "field-input", "dir": "ltr"}),
    )

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        if p2 and len(p2) < 6:
            raise forms.ValidationError("رمز عبور باید حداقل ۶ نویسه باشد.")
        return p2


class MyProfileForm(forms.Form):
    full_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "field-input"}),
    )
    phone = forms.CharField(
        label="شماره تماس",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "field-input", "dir": "ltr"}),
    )


class ChangeMyPasswordForm(forms.Form):
    current_password = forms.CharField(
        label="رمز فعلی",
        widget=forms.PasswordInput(attrs={"class": "field-input", "dir": "ltr"}),
    )
    password1 = forms.CharField(
        label="رمز جدید", widget=forms.PasswordInput(attrs={"class": "field-input", "dir": "ltr"})
    )
    password2 = forms.CharField(
        label="تکرار رمز جدید",
        widget=forms.PasswordInput(attrs={"class": "field-input", "dir": "ltr"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data.get("current_password")
        if self.user and not self.user.check_password(password):
            raise forms.ValidationError("رمز فعلی درست نیست.")
        return password

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("رمز جدید و تکرار آن یکسان نیستند.")
        if p2 and len(p2) < 6:
            raise forms.ValidationError("رمز عبور باید حداقل ۶ نویسه باشد.")
        return p2


class KhoneLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "dir": "ltr",
                "autofocus": True,
                "autocapitalize": "none",
                "autocomplete": "username",
                "placeholder": "نام کاربری",
            }
        ),
    )
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(
            attrs={
                "class": "field-input",
                "dir": "ltr",
                "autocomplete": "current-password",
                "placeholder": "رمز عبور",
            }
        ),
    )
    error_messages = {
        "invalid_login": "نام کاربری یا رمز عبور درست نیست.",
        "inactive": "این حساب غیرفعال شده است.",
    }
