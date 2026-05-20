from django.contrib import admin

from .models import Case, CaseLitigant


class CaseLitigantInline(admin.StackedInline):
    model = CaseLitigant
    extra = 1


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "case_number", "title", "created_at")
    list_display_links = ("title",)
    search_fields = ("case_number", "title")
    readonly_fields = ("uuid",)
    ordering = ("-id",)
    inlines = (CaseLitigantInline,)
