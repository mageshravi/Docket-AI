from django.contrib import admin

from .models import Timeline, TimelineEvent, TimelineExhibit


class TimelineExhibitInline(admin.TabularInline):
    model = TimelineExhibit
    extra = 1
    verbose_name = "Timeline Exhibit"
    verbose_name_plural = "Timeline Exhibits"


@admin.register(Timeline)
class TimelineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "case",
        "event_extraction_status",
    )
    list_display_links = ("name",)
    list_filter = ("event_extraction_status",)
    readonly_fields = ("created_by",)
    ordering = ("-created_at",)
    inlines = [TimelineExhibitInline]


@admin.register(TimelineEvent)
class TimelineEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "timeline", "event_date")
    list_display_links = ("title",)
    ordering = ("-created_at",)
