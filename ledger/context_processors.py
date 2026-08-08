from django.utils import timezone

from .models import get_profile
from .utils import jalali


def app_context(request):
    """اطلاعات مشترک همه صفحه‌ها: نام برنامه، پروفایل کاربر، تاریخ و ساعت تهران."""
    now = timezone.localtime()
    profile = get_profile(getattr(request, "user", None))
    return {
        "APP_NAME": "حساب‌کتاب ساخت‌وساز",
        "APP_SHORT_NAME": "خونه",
        "profile": profile,
        "today_jalali": jalali.format_jalali_full(now.date()),
        "today_jalali_short": jalali.format_jalali(now.date()),
        "now_time": jalali.to_persian_digits(now.strftime("%H:%M")),
    }
