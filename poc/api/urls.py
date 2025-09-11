from django.urls import path

from poc.api.views import (
    ListCreateMessageAPI,
    ListCreateThreadAPI,
    ListCreateUploadedFileAPI,
)

app_name = "poc"
urlpatterns = [
    path("uploaded-files/", ListCreateUploadedFileAPI.as_view(), name="uploaded_files"),
    path(
        "cases/<uuid:case_uuid>/chat-threads/",
        ListCreateThreadAPI.as_view(),
        name="chat_threads",
    ),
    path(
        "cases/<uuid:case_uuid>/chat-threads/<uuid:thread_uuid>/messages/",
        ListCreateMessageAPI.as_view(),
        name="chat_messages",
    ),
]
