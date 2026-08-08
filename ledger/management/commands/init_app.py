"""
راه‌اندازی اولیه برنامه: ساخت حساب مدیر و دسته‌بندی‌های پیش‌فرض.

مثال:
    python manage.py init_app --username admin --password 123456 --name "علی محمدی"
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ledger.models import ROLE_OWNER, Category, Profile, create_default_categories


class Command(BaseCommand):
    help = "ساخت حساب مدیر و دسته‌بندی‌های پیش‌فرض"

    def add_arguments(self, parser):
        parser.add_argument("--username", default=None, help="نام کاربری مدیر")
        parser.add_argument("--password", default=None, help="رمز عبور مدیر")
        parser.add_argument("--name", default="", help="نام و نام خانوادگی مدیر")
        parser.add_argument(
            "--skip-categories",
            action="store_true",
            help="دسته‌بندی‌های پیش‌فرض ساخته نشود",
        )

    def handle(self, *args, **options):
        owner = None
        username = options.get("username")
        password = options.get("password")

        if username and password:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": True, "is_superuser": True},
            )
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            full_name = (options.get("name") or "").strip()
            if full_name:
                parts = full_name.split(" ", 1)
                user.first_name = parts[0][:150]
                user.last_name = (parts[1] if len(parts) > 1 else "")[:150]
            user.save()

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = ROLE_OWNER
            if full_name:
                profile.full_name = full_name
            profile.can_view_all = True
            profile.save()
            owner = user

            self.stdout.write(
                self.style.SUCCESS(
                    ("حساب مدیر ساخته شد: %s" if created else "رمز حساب مدیر به‌روزرسانی شد: %s")
                    % username
                )
            )
        else:
            owner = User.objects.filter(is_superuser=True).order_by("id").first()
            self.stdout.write(
                "برای ساخت حساب مدیر از --username و --password استفاده کنید "
                "(یا دستور createsuperuser)."
            )

        if not options.get("skip_categories"):
            before = Category.objects.count()
            create_default_categories(owner)
            after = Category.objects.count()
            self.stdout.write(
                self.style.SUCCESS("دسته‌بندی‌ها آماده شد (%d دسته جدید)." % (after - before))
            )

        self.stdout.write(self.style.SUCCESS("راه‌اندازی کامل شد. اجرا: python manage.py runserver"))
