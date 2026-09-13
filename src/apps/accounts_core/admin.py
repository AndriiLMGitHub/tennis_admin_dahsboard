from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

User = get_user_model()


@admin.register(User)
class AccountUserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "date_joined")
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "date_joined",
        "user_status",
        "role",
    )
    search_fields = ("email", "first_name", "last_name", "coach_status")
    ordering = ("email",)
    date_hierarchy = "date_joined"
    readonly_fields = ("date_joined", "last_login", "password",)

    fieldsets = (
        (_("Main"), {"fields": ("email", "role", "user_status", "telegram_chat_id")}),
        (_("Readonly fields"), {"fields": ("password",)}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "avatar", "country", "currency", "language", "timezone",
                        "phone_number", "company_site", "company")},
        ),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (_("Create user"), {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    add_form_template = None

    model = User
