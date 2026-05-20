from django.contrib import admin

from litigants.models import Litigant, LitigantRole


@admin.register(Litigant)
class LitigantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "bio", "phone", "created_at")
    list_display_links = ("name",)
    search_fields = ("name", "bio", "phone", "email")
    ordering = ("-id",)


@admin.register(LitigantRole)
class LitigantRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "handle", "created_at")
    list_display_links = ("handle",)
    search_fields = ("name", "handle")
    ordering = ("-id",)
