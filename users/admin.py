from django.contrib import admin

from .models import TgUser


@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "username",
        "tg_id",
        "balance",
        "points",
        "is_admin",
        "created_at",
        "updated_at",
    )
