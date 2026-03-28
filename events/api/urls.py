from django.urls import path

from events.api.views import (
    ListCreateTimelineAPI,
    ListTimelineEventsAPI,
    ListTimelineExhibitsAPI,
    RetrieveTimelineAPI,
)

app_name = "events"
urlpatterns = [
    path("timelines/", ListCreateTimelineAPI.as_view(), name="timelines"),
    path(
        "timelines/<int:timeline_id>/",
        RetrieveTimelineAPI.as_view(),
        name="timeline_detail",
    ),
    path(
        "timelines/<int:timeline_id>/events/",
        ListTimelineEventsAPI.as_view(),
        name="timeline_events",
    ),
    path(
        "timelines/<int:timeline_id>/exhibits/",
        ListTimelineExhibitsAPI.as_view(),
        name="timeline_exhibits",
    ),
]
