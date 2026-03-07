from django.urls import path

from events.api.views import ListCreateTimelineAPI

app_name = "events"
urlpatterns = [
    path("timelines/", ListCreateTimelineAPI.as_view(), name="timelines"),
]
