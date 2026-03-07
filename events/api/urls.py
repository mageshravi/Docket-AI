from django.urls import path

from events.api.views import CreateTimelineAPI

app_name = "events"
urlpatterns = [
    path("timelines/", CreateTimelineAPI.as_view(), name="timelines"),
]
