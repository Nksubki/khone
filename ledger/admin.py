from django.contrib import admin

from .models import ActivityLog, Category, Profile, Project, Transaction


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "role", "phone", "can_view_all")
    list_filter = ("role", "can_view_all")
    search_fields = ("full_name", "user__username", "phone")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "icon", "color", "is_active", "sort_order")
    list_filter = ("kind", "is_active")
    search_fields = ("name",)
    list_editable = ("sort_order", "is_active")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "budget", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "address")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "jalali_date", "kind", "amount", "category", "created_by")
    list_filter = ("kind", "category", "payment_method", "created_by")
    search_fields = ("description", "payee")
    date_hierarchy = "date"
    autocomplete_fields = ("category",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "summary")
    list_filter = ("action",)
    search_fields = ("summary",)
