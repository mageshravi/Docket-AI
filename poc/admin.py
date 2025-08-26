from django.contrib import admin

from .models import Case, CaseLitigant, ChatThread, Litigant, UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "status", "created_at")
    list_display_links = ("file_name",)
    list_filter = ("status",)
    search_fields = ("file_name",)
    ordering = ("-id",)

    def file_name(self, obj):
        return obj.file.name.split("/")[-1]

    file_name.short_description = "File Name"


class CaseLitigantInline(admin.StackedInline):
    model = CaseLitigant
    extra = 1


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "case_number", "title", "created_at")
    list_display_links = ("title",)
    search_fields = ("case_number", "title")
    ordering = ("-id",)
    inlines = (CaseLitigantInline,)


@admin.register(Litigant)
class LitigantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "bio", "phone", "created_at")
    list_display_links = ("name",)
    search_fields = ("name", "bio", "phone", "email")
    ordering = ("-id",)


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "case", "created_at")
    list_display_links = ("title",)
    search_fields = (
        "title",
        "case__case_number",
    )
    ordering = ("-id",)
