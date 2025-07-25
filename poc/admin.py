from django.contrib import admin

from .models import UploadedFile


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
