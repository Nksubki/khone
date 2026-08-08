"""ویوهای برنامه حسابداری ساخت‌وساز."""
import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import filters as flt
from .forms import (
    CategoryForm,
    ChangeMyPasswordForm,
    KhoneLoginForm,
    MyProfileForm,
    PartnerCreateForm,
    PartnerEditForm,
    ProjectForm,
    ResetPasswordForm,
    TransactionForm,
)
from .models import (
    KIND_EXPENSE,
    KIND_INCOME,
    PAYMENT_CHOICES,
    ROLE_CHOICES,
    ActivityLog,
    Category,
    Project,
    Transaction,
    get_profile,
    log_activity,
)
from .utils import jalali
from .utils.numbers import format_money, humanize_amount, parse_amount

PAGE_SIZE = 25


# --------------------------------------------------------------------------- #
#  دسترسی‌ها
# --------------------------------------------------------------------------- #
def owner_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not profile.can_manage_users:
            messages.error(request, "این بخش فقط برای مدیر است.")
            return redirect("ledger:dashboard")
        return view(request, *args, **kwargs)

    return wrapper


def editor_required(view):
    """ناظرها اجازه ثبت/ویرایش ندارند."""

    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = get_profile(request.user)
        if not profile or not profile.can_add_records:
            messages.error(request, "حساب شما فقط اجازه مشاهده دارد.")
            return redirect("ledger:dashboard")
        return view(request, *args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------- #
#  ورود و خروج
# --------------------------------------------------------------------------- #
def login_view(request):
    if request.user.is_authenticated:
        return redirect("ledger:dashboard")

    form = KhoneLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        get_profile(user)
        log_activity(user, "login", "ورود به برنامه")
        messages.success(request, "خوش آمدید 👋")
        next_url = request.GET.get("next") or request.POST.get("next")
        return redirect(next_url or "ledger:dashboard")

    now = timezone.localtime()
    return render(
        request,
        "ledger/login.html",
        {
            "form": form,
            "today_full": jalali.format_jalali_full(now.date()),
            "now_time": jalali.to_persian_digits(now.strftime("%H:%M")),
        },
    )


def logout_view(request):
    auth_logout(request)
    messages.info(request, "از حساب خود خارج شدید.")
    return redirect("ledger:login")


# --------------------------------------------------------------------------- #
#  داشبورد
# --------------------------------------------------------------------------- #
@login_required
def dashboard(request):
    profile = get_profile(request.user)
    today = timezone.localdate()
    jy, jm, _ = jalali.to_jalali(today)

    visible = Transaction.objects.visible_to(request.user)

    month_start, month_end = jalali.jalali_month_range(jy, jm)
    month_qs = visible.in_range(month_start, month_end)
    week_start, week_end = jalali.week_range(today)

    month_summary = flt.summarize(month_qs)
    all_summary = flt.summarize(visible)

    top_categories, _ = flt.group_by_category(month_qs)
    by_user, _ = flt.group_by_user(month_qs)

    months = jalali.last_jalali_months(today, 6)
    month_series = flt.group_by_month(
        visible.in_range(months[0][2], months[-1][3]), months=months
    )
    day_series = flt.group_by_day(visible, days=14, today=today)

    my_month_total = month_qs.filter(created_by=request.user, kind=KIND_EXPENSE).total()

    context = {
        "page_title": "داشبورد",
        "today": today,
        "month_label": jalali.format_jalali_month(jy, jm),
        "today_expense": visible.filter(date=today, kind=KIND_EXPENSE).total(),
        "today_count": visible.filter(date=today).count(),
        "week_expense": visible.in_range(week_start, week_end).filter(kind=KIND_EXPENSE).total(),
        "month_summary": month_summary,
        "all_summary": all_summary,
        "my_month_total": my_month_total,
        "top_categories": top_categories[:6],
        "by_user": by_user,
        "month_series": month_series,
        "day_series": day_series,
        "recent": visible.with_relations()[:8],
        "projects": Project.objects.filter(is_active=True)[:4],
        "category_count": Category.objects.filter(is_active=True).count(),
        "user_count": User.objects.filter(is_active=True).count(),
        "profile": profile,
    }
    return render(request, "ledger/dashboard.html", context)


# --------------------------------------------------------------------------- #
#  فهرست تراکنش‌ها + فیلترها
# --------------------------------------------------------------------------- #
def _filter_context(request):
    """داده‌های مشترک صفحه فیلتر (فهرست و گزارش)."""
    tf = flt.TransactionFilter(request)
    queryset = tf.queryset()
    for error in tf.errors:
        messages.warning(request, error)

    categories = Category.objects.filter(is_active=True).order_by("sort_order", "name")
    users = (
        User.objects.filter(transactions__isnull=False)
        .select_related("profile")
        .distinct()
        .order_by("username")
    )
    return {
        "filters": tf,
        "queryset": queryset,
        "all_categories": categories,
        "all_users": users,
        "all_projects": Project.objects.all(),
        "range_choices": flt.RANGE_CHOICES,
        "sort_choices": flt.SORT_CHOICES,
        "payment_choices": PAYMENT_CHOICES,
    }


@login_required
def transaction_list(request):
    data = _filter_context(request)
    queryset = data["queryset"]
    summary = flt.summarize(queryset)

    paginator = Paginator(queryset, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    category_rows, _ = flt.group_by_category(queryset)
    user_rows, _ = flt.group_by_user(queryset)

    context = dict(data)
    context.update(
        {
            "page_title": "هزینه‌ها و دریافتی‌ها",
            "page_obj": page,
            "transactions": page.object_list,
            "summary": summary,
            "category_rows": category_rows[:8],
            "user_rows": user_rows,
            "total_count": paginator.count,
        }
    )
    return render(request, "ledger/transaction_list.html", context)


@login_required
def transaction_detail(request, pk):
    profile = get_profile(request.user)
    queryset = Transaction.objects.with_relations()
    if not (profile and profile.sees_everything):
        queryset = queryset.filter(created_by=request.user)
    transaction = get_object_or_404(queryset, pk=pk)
    return render(
        request,
        "ledger/transaction_detail.html",
        {
            "page_title": "جزئیات رکورد",
            "tx": transaction,
            "can_edit": transaction.can_edit(request.user),
        },
    )


@editor_required
def transaction_create(request):
    initial = {}
    kind = request.GET.get("kind")
    if kind in (KIND_EXPENSE, KIND_INCOME):
        initial["kind"] = kind
    category_id = request.GET.get("cat")
    if category_id:
        initial["category"] = category_id

    if request.method == "POST":
        form = TransactionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.created_by = request.user
            tx.voice_used = request.POST.get("voice_used") == "1"
            tx.save()
            log_activity(
                request.user,
                "create",
                "ثبت %s در دسته %s به مبلغ %s تومان"
                % (tx.get_kind_display(), tx.category.name, format_money(tx.amount, persian=False)),
            )
            messages.success(
                request,
                "ثبت شد: %s تومان (%s) — %s"
                % (format_money(tx.amount), humanize_amount(tx.amount), tx.category.name),
            )
            if request.POST.get("save_and_new") == "1":
                return redirect(reverse("ledger:transaction_create") + "?kind=%s" % tx.kind)
            return redirect("ledger:transaction_list")
        messages.error(request, "فرم کامل نیست؛ موارد مشخص‌شده را اصلاح کنید.")
    else:
        form = TransactionForm(initial=initial, user=request.user)

    return render(
        request,
        "ledger/transaction_form.html",
        {
            "page_title": "ثبت هزینه جدید",
            "form": form,
            "is_new": True,
            "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
        },
    )


@editor_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if not transaction.can_edit(request.user):
        messages.error(request, "اجازه ویرایش این رکورد را ندارید.")
        return redirect("ledger:transaction_list")

    if request.method == "POST":
        form = TransactionForm(
            request.POST, request.FILES, instance=transaction, user=request.user
        )
        if form.is_valid():
            tx = form.save()
            log_activity(
                request.user,
                "update",
                "ویرایش رکورد #%d (%s تومان)" % (tx.pk, format_money(tx.amount, persian=False)),
            )
            messages.success(request, "تغییرات ذخیره شد.")
            return redirect("ledger:transaction_detail", pk=tx.pk)
        messages.error(request, "فرم کامل نیست؛ موارد مشخص‌شده را اصلاح کنید.")
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    return render(
        request,
        "ledger/transaction_form.html",
        {
            "page_title": "ویرایش رکورد",
            "form": form,
            "is_new": False,
            "tx": transaction,
            "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
        },
    )


@editor_required
@require_POST
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if not transaction.can_edit(request.user):
        messages.error(request, "اجازه حذف این رکورد را ندارید.")
        return redirect("ledger:transaction_list")
    amount = transaction.amount
    name = transaction.category.name
    transaction.delete()
    log_activity(
        request.user,
        "delete",
        "حذف رکورد %s تومان از دسته %s" % (format_money(amount, persian=False), name),
    )
    messages.success(request, "رکورد حذف شد.")
    return redirect("ledger:transaction_list")


@login_required
def transaction_export(request):
    """خروجی CSV از نتیجه فیلتر فعلی (مناسب اکسل)."""
    tf = flt.TransactionFilter(request)
    queryset = tf.queryset()

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = "khone-export-%s.csv" % jalali.format_jalali(
        timezone.localdate(), persian_digits=False
    ).replace("/", "-")
    response["Content-Disposition"] = 'attachment; filename="%s"' % filename
    response.write("\ufeff")  # BOM برای نمایش درست فارسی در اکسل

    writer = csv.writer(response)
    writer.writerow(
        [
            "ردیف",
            "تاریخ شمسی",
            "روز هفته",
            "ساعت",
            "نوع",
            "دسته‌بندی",
            "پروژه",
            "مبلغ (تومان)",
            "نحوه پرداخت",
            "طرف حساب",
            "توضیحات",
            "ثبت‌کننده",
            "زمان ثبت",
        ]
    )
    for index, tx in enumerate(queryset, start=1):
        profile = getattr(tx.created_by, "profile", None)
        writer.writerow(
            [
                index,
                jalali.format_jalali(tx.date, persian_digits=False),
                jalali.weekday_name(tx.date),
                tx.time.strftime("%H:%M") if tx.time else "",
                tx.get_kind_display(),
                tx.category.name if tx.category_id else "",
                tx.project.name if tx.project_id else "",
                tx.amount,
                tx.get_payment_method_display(),
                tx.payee,
                (tx.description or "").replace("\n", " "),
                profile.display_name if profile else tx.created_by.username,
                jalali.format_jalali(timezone.localtime(tx.created_at).date(), persian_digits=False),
            ]
        )
    return response


# --------------------------------------------------------------------------- #
#  گزارش‌ها
# --------------------------------------------------------------------------- #
@login_required
def reports(request):
    data = _filter_context(request)
    queryset = data["queryset"]
    summary = flt.summarize(queryset)

    kind = KIND_INCOME if data["filters"].kind == KIND_INCOME else KIND_EXPENSE

    category_rows, category_total = flt.group_by_category(queryset, kind)
    user_rows, _ = flt.group_by_user(queryset, kind)
    project_rows, _ = flt.group_by_project(queryset, kind)
    payment_rows, _ = flt.group_by_payment(queryset, kind)

    months = jalali.last_jalali_months(timezone.localdate(), 12)
    month_series = flt.group_by_month(
        Transaction.objects.visible_to(request.user).in_range(months[0][2], months[-1][3]),
        kind,
        months=months,
    )

    biggest = queryset.filter(kind=kind).order_by("-amount")[:10]

    context = dict(data)
    context.update(
        {
            "page_title": "گزارش‌ها و تحلیل",
            "summary": summary,
            "category_rows": category_rows,
            "category_total": category_total,
            "user_rows": user_rows,
            "project_rows": project_rows,
            "payment_rows": payment_rows,
            "month_series": month_series,
            "biggest": biggest,
            "report_kind": kind,
        }
    )
    return render(request, "ledger/reports.html", context)


# --------------------------------------------------------------------------- #
#  دسته‌بندی‌ها
# --------------------------------------------------------------------------- #
@login_required
def category_list(request):
    profile = get_profile(request.user)
    visible = Transaction.objects.visible_to(request.user)
    totals = {
        row["category"]: (row["total"] or 0, row["count"])
        for row in visible.order_by()
        .values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
    }
    categories = []
    for category in Category.objects.all().order_by("kind", "sort_order", "name"):
        total, count = totals.get(category.id, (0, 0))
        categories.append({"obj": category, "total": total, "count": count})

    return render(
        request,
        "ledger/category_list.html",
        {
            "page_title": "دسته‌بندی‌ها",
            "categories": categories,
            "can_manage": bool(profile and profile.can_manage_categories),
            "can_delete": bool(profile and profile.can_delete_categories),
        },
    )


@editor_required
def category_create(request):
    profile = get_profile(request.user)
    if not profile.can_manage_categories:
        messages.error(request, "اجازه ساخت دسته‌بندی را ندارید.")
        return redirect("ledger:category_list")

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            if not category.sort_order:
                last = Category.objects.order_by("-sort_order").first()
                category.sort_order = (last.sort_order if last else 0) + 10
            category.save()
            log_activity(request.user, "category", "ساخت دسته‌بندی %s" % category.name)
            messages.success(request, "دسته‌بندی «%s» ساخته شد." % category.name)
            next_url = request.POST.get("next")
            return redirect(next_url or "ledger:category_list")
    else:
        form = CategoryForm()

    return render(
        request,
        "ledger/category_form.html",
        {"page_title": "دسته‌بندی جدید", "form": form, "is_new": True},
    )


@editor_required
def category_edit(request, pk):
    profile = get_profile(request.user)
    category = get_object_or_404(Category, pk=pk)
    if not profile.can_manage_categories:
        messages.error(request, "اجازه ویرایش دسته‌بندی را ندارید.")
        return redirect("ledger:category_list")

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            log_activity(request.user, "category", "ویرایش دسته‌بندی %s" % category.name)
            messages.success(request, "دسته‌بندی به‌روزرسانی شد.")
            return redirect("ledger:category_list")
    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "ledger/category_form.html",
        {
            "page_title": "ویرایش دسته‌بندی",
            "form": form,
            "is_new": False,
            "category": category,
        },
    )


@owner_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.transactions.exists():
        category.is_active = False
        category.save(update_fields=["is_active"])
        messages.warning(
            request,
            "این دسته‌بندی رکورد ثبت‌شده دارد، پس حذف نشد ولی غیرفعال شد "
            "(در فرم ثبت جدید نمایش داده نمی‌شود).",
        )
    else:
        name = category.name
        category.delete()
        log_activity(request.user, "category", "حذف دسته‌بندی %s" % name)
        messages.success(request, "دسته‌بندی حذف شد.")
    return redirect("ledger:category_list")


@editor_required
@require_POST
def category_quick_create(request):
    """ساخت سریع دسته‌بندی از داخل فرم ثبت هزینه (بدون ترک صفحه)."""
    name = (request.POST.get("name") or "").strip()
    kind = request.POST.get("kind") or KIND_EXPENSE
    icon = (request.POST.get("icon") or "🧱").strip()[:8]
    if not name:
        return JsonResponse({"ok": False, "error": "نام دسته‌بندی خالی است."}, status=400)
    if Category.objects.filter(name__iexact=name).exists():
        category = Category.objects.filter(name__iexact=name).first()
        return JsonResponse(
            {"ok": True, "existing": True, "id": category.id, "label": category.label}
        )
    last = Category.objects.order_by("-sort_order").first()
    category = Category.objects.create(
        name=name,
        kind=kind if kind in (KIND_EXPENSE, KIND_INCOME) else KIND_EXPENSE,
        icon=icon,
        sort_order=(last.sort_order if last else 0) + 10,
        created_by=request.user,
    )
    log_activity(request.user, "category", "ساخت سریع دسته‌بندی %s" % category.name)
    return JsonResponse(
        {"ok": True, "existing": False, "id": category.id, "label": category.label,
         "kind": category.kind}
    )


# --------------------------------------------------------------------------- #
#  پروژه‌ها
# --------------------------------------------------------------------------- #
@login_required
def project_list(request):
    profile = get_profile(request.user)
    visible = Transaction.objects.visible_to(request.user)
    rows = []
    for project in Project.objects.all():
        project_qs = visible.filter(project=project)
        expense = project_qs.filter(kind=KIND_EXPENSE).total()
        income = project_qs.filter(kind=KIND_INCOME).total()
        percent = None
        if project.budget:
            percent = min(100, round(expense * 100 / project.budget, 1))
        rows.append(
            {
                "obj": project,
                "expense": expense,
                "income": income,
                "balance": income - expense,
                "count": project_qs.count(),
                "percent": percent,
            }
        )
    no_project = visible.filter(project__isnull=True)
    return render(
        request,
        "ledger/project_list.html",
        {
            "page_title": "پروژه‌ها",
            "rows": rows,
            "can_manage": bool(profile and profile.can_add_records),
            "no_project_total": no_project.filter(kind=KIND_EXPENSE).total(),
            "no_project_count": no_project.count(),
        },
    )


@editor_required
def project_create(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            log_activity(request.user, "project", "ساخت پروژه %s" % project.name)
            messages.success(request, "پروژه «%s» ساخته شد." % project.name)
            return redirect("ledger:project_list")
    else:
        form = ProjectForm()
    return render(
        request,
        "ledger/project_form.html",
        {"page_title": "پروژه جدید", "form": form, "is_new": True},
    )


@editor_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_activity(request.user, "project", "ویرایش پروژه %s" % project.name)
            messages.success(request, "پروژه به‌روزرسانی شد.")
            return redirect("ledger:project_list")
    else:
        form = ProjectForm(instance=project)
    return render(
        request,
        "ledger/project_form.html",
        {
            "page_title": "ویرایش پروژه",
            "form": form,
            "is_new": False,
            "project": project,
        },
    )


# --------------------------------------------------------------------------- #
#  کاربران (شرکا)
# --------------------------------------------------------------------------- #
@owner_required
def user_list(request):
    today = timezone.localdate()
    jy, jm, _ = jalali.to_jalali(today)
    month_start, month_end = jalali.jalali_month_range(jy, jm)

    rows = []
    for user in User.objects.select_related("profile").order_by("-is_active", "username"):
        profile = get_profile(user)
        user_qs = Transaction.objects.filter(created_by=user)
        rows.append(
            {
                "user": user,
                "profile": profile,
                "total": user_qs.filter(kind=KIND_EXPENSE).total(),
                "month_total": user_qs.in_range(month_start, month_end)
                .filter(kind=KIND_EXPENSE)
                .total(),
                "count": user_qs.count(),
                "last": user_qs.order_by("-created_at").first(),
            }
        )
    return render(
        request,
        "ledger/user_list.html",
        {
            "page_title": "کاربران و شرکا",
            "rows": rows,
            "month_label": jalali.format_jalali_month(jy, jm),
        },
    )


@owner_required
def user_create(request):
    if request.method == "POST":
        form = PartnerCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(request.user, "user", "ساخت حساب برای %s" % user.username)
            messages.success(
                request,
                "حساب «%s» ساخته شد. نام کاربری: %s"
                % (form.cleaned_data["full_name"], user.username),
            )
            return redirect("ledger:user_list")
    else:
        form = PartnerCreateForm()
    return render(
        request,
        "ledger/user_form.html",
        {"page_title": "کاربر جدید", "form": form, "is_new": True, "roles": ROLE_CHOICES},
    )


@owner_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = get_profile(user)

    if request.method == "POST":
        form = PartnerEditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            profile.full_name = data["full_name"].strip()
            profile.phone = data.get("phone", "")
            profile.note = data.get("note", "")
            if user.is_superuser:
                profile.role = "owner"
            else:
                profile.role = data["role"]
            profile.can_view_all = bool(data.get("can_view_all"))
            profile.save()

            parts = profile.full_name.split(" ", 1)
            user.first_name = parts[0][:150]
            user.last_name = (parts[1] if len(parts) > 1 else "")[:150]
            if user.id != request.user.id:
                user.is_active = bool(data.get("is_active"))
            user.save()

            log_activity(request.user, "user", "ویرایش حساب %s" % user.username)
            messages.success(request, "اطلاعات کاربر ذخیره شد.")
            return redirect("ledger:user_list")
    else:
        form = PartnerEditForm(
            initial={
                "full_name": profile.display_name,
                "phone": profile.phone,
                "role": profile.role,
                "can_view_all": profile.can_view_all,
                "is_active": user.is_active,
                "note": profile.note,
            }
        )

    return render(
        request,
        "ledger/user_form.html",
        {
            "page_title": "ویرایش کاربر",
            "form": form,
            "is_new": False,
            "target_user": user,
            "target_profile": profile,
            "is_self": user.id == request.user.id,
        },
    )


@owner_required
def user_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.save()
            if user.id == request.user.id:
                update_session_auth_hash(request, user)
            log_activity(request.user, "user", "تغییر رمز %s" % user.username)
            messages.success(request, "رمز عبور کاربر تغییر کرد.")
            return redirect("ledger:user_list")
    else:
        form = ResetPasswordForm()
    return render(
        request,
        "ledger/user_password.html",
        {
            "page_title": "تغییر رمز کاربر",
            "form": form,
            "target_user": user,
            "target_profile": get_profile(user),
        },
    )


@login_required
def my_profile(request):
    profile = get_profile(request.user)
    profile_form = MyProfileForm(
        initial={"full_name": profile.display_name, "phone": profile.phone}
    )
    password_form = ChangeMyPasswordForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            profile_form = MyProfileForm(request.POST)
            if profile_form.is_valid():
                profile.full_name = profile_form.cleaned_data["full_name"].strip()
                profile.phone = profile_form.cleaned_data.get("phone", "")
                profile.save()
                parts = profile.full_name.split(" ", 1)
                request.user.first_name = parts[0][:150]
                request.user.last_name = (parts[1] if len(parts) > 1 else "")[:150]
                request.user.save()
                messages.success(request, "مشخصات شما ذخیره شد.")
                return redirect("ledger:my_profile")
        elif action == "password":
            password_form = ChangeMyPasswordForm(request.POST, user=request.user)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data["password1"])
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "رمز عبور شما تغییر کرد.")
                return redirect("ledger:my_profile")

    my_qs = Transaction.objects.filter(created_by=request.user)
    today = timezone.localdate()
    jy, jm, _ = jalali.to_jalali(today)
    month_start, month_end = jalali.jalali_month_range(jy, jm)

    return render(
        request,
        "ledger/profile.html",
        {
            "page_title": "حساب من",
            "profile_form": profile_form,
            "password_form": password_form,
            "my_total": my_qs.filter(kind=KIND_EXPENSE).total(),
            "my_month": my_qs.in_range(month_start, month_end).filter(kind=KIND_EXPENSE).total(),
            "my_count": my_qs.count(),
            "month_label": jalali.format_jalali_month(jy, jm),
        },
    )


@login_required
def activity_list(request):
    profile = get_profile(request.user)
    queryset = ActivityLog.objects.select_related("user", "user__profile")
    if not (profile and profile.is_owner):
        queryset = queryset.filter(user=request.user)

    paginator = Paginator(queryset, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "ledger/activity_list.html",
        {"page_title": "گزارش فعالیت‌ها", "page_obj": page, "logs": page.object_list},
    )


# --------------------------------------------------------------------------- #
#  API کوچک برای ورودی صوتی
# --------------------------------------------------------------------------- #
@login_required
@require_POST
def api_parse_amount(request):
    """متن فارسی (مثل «صد و بیست میلیون») را به عدد تبدیل می‌کند."""
    text = request.POST.get("text") or ""
    value = parse_amount(text)
    if value is None:
        return JsonResponse({"ok": False, "text": text})
    return JsonResponse(
        {
            "ok": True,
            "value": value,
            "formatted": "{:,}".format(value),
            "words": humanize_amount(value),
        }
    )


@login_required
def api_today(request):
    """تاریخ و ساعت جاری تهران (برای پیش‌فرض فرم‌ها)."""
    now = timezone.localtime()
    jy, jm, jd = jalali.to_jalali(now.date())
    return JsonResponse(
        {
            "jalali": "%04d/%02d/%02d" % (jy, jm, jd),
            "long": jalali.format_jalali_full(now.date()),
            "time": now.strftime("%H:%M"),
        }
    )
