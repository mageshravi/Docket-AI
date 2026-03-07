from django.urls import path

from events.api.views import ListCreateTimelineAPI, ListTimelineEventAPI

app_name = "events"
urlpatterns = [
    path("timelines/", ListCreateTimelineAPI.as_view(), name="timelines"),
    path(
        "timelines/<int:timeline_id>/",
        ListTimelineEventAPI.as_view(),
        name="timeline_events",
    ),
]
