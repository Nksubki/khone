from django.urls import path

from . import views

app_name = "ledger"

urlpatterns = [
    # ورود و خروج
    path("vorod/", views.login_view, name="login"),
    path("khorooj/", views.logout_view, name="logout"),

    # داشبورد
    path("", views.dashboard, name="dashboard"),

    # تراکنش‌ها
    path("hazine/", views.transaction_list, name="transaction_list"),
    path("hazine/jadid/", views.transaction_create, name="transaction_create"),
    path("hazine/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("hazine/<int:pk>/virayesh/", views.transaction_edit, name="transaction_edit"),
    path("hazine/<int:pk>/hazf/", views.transaction_delete, name="transaction_delete"),
    path("hazine/export/", views.transaction_export, name="transaction_export"),

    # گزارش‌ها
    path("gozaresh/", views.reports, name="reports"),

    # دسته‌بندی‌ها
    path("dastebandi/", views.category_list, name="category_list"),
    path("dastebandi/jadid/", views.category_create, name="category_create"),
    path("dastebandi/<int:pk>/virayesh/", views.category_edit, name="category_edit"),
    path("dastebandi/<int:pk>/hazf/", views.category_delete, name="category_delete"),
    path("dastebandi/sari/", views.category_quick_create, name="category_quick_create"),

    # پروژه‌ها
    path("porozhe/", views.project_list, name="project_list"),
    path("porozhe/jadid/", views.project_create, name="project_create"),
    path("porozhe/<int:pk>/virayesh/", views.project_edit, name="project_edit"),

    # کاربران
    path("karbaran/", views.user_list, name="user_list"),
    path("karbaran/jadid/", views.user_create, name="user_create"),
    path("karbaran/<int:pk>/virayesh/", views.user_edit, name="user_edit"),
    path("karbaran/<int:pk>/ramz/", views.user_password, name="user_password"),

    # حساب من و فعالیت‌ها
    path("hesab-man/", views.my_profile, name="my_profile"),
    path("faaliyat/", views.activity_list, name="activity_list"),

    # API کوچک
    path("api/parse-amount/", views.api_parse_amount, name="api_parse_amount"),
    path("api/today/", views.api_today, name="api_today"),
]
