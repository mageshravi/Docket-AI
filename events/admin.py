from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "case",
        "event_date",
        "display_title",
    )
    list_display_links = ("display_title",)
    list_filter = (
        "case",
        "source_entity",
    )
    ordering = ("-event_date",)

    def display_title(self, obj):
        return obj.get_display_title()
