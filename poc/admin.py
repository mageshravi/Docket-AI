from django.contrib import admin

from .models import (
    ChatThread,
    ParsedEmail,
    ParsedEmailAttachment,
    UploadedFile,
)


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "case", "created_at")
    list_display_links = ("title",)
    search_fields = (
        "title",
        "case__case_number",
    )
    ordering = ("-id",)


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "filename",
        "file_name",
        "is_active",
        "embedding_status",
        "created_at",
    )
    list_display_links = ("file_name",)
    list_filter = ("embedding_status", "is_deleted")
    search_fields = ("file_name",)
    ordering = ("-id",)

    def file_name(self, obj):
        return obj.file.name.split("/")[-1]

    def is_active(self, obj):
        return not obj.is_deleted

    file_name.short_description = "File Name"
    is_active.boolean = True


@admin.register(ParsedEmail)
class ParsedEmailAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "sender",
        "sent_on",
        "embedding_status",
        "created_at",
    )
    list_display_links = ("subject",)
    list_filter = ("embedding_status",)
    ordering = ("-id",)


@admin.register(ParsedEmailAttachment)
class ParsedEmailAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "filename",
        "embedding_status",
        "created_at",
    )
    list_display_links = ("filename",)
    list_filter = ("embedding_status",)
    ordering = ("-id",)
