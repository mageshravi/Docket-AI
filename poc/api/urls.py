from django.urls import path

from poc.api.views import (
    ListCreateCaseAPI,
    ListCreateMessageAPI,
    ListCreateThreadAPI,
    ListCreateUploadedFileAPI,
    RetrieveUpdateCaseAPI,
    RetrieveUpdateDestroyUploadedFileAPI,
)

app_name = "poc"
urlpatterns = [
    path("cases/", ListCreateCaseAPI.as_view(), name="cases"),
    path(
        "cases/<uuid:case_uuid>/", RetrieveUpdateCaseAPI.as_view(), name="case_detail"
    ),
    path(
        "cases/<uuid:case_uuid>/exhibits/",
        ListCreateUploadedFileAPI.as_view(),
        name="exhibits",
    ),
    path(
        "cases/<uuid:case_uuid>/exhibits/<int:id>/",
        RetrieveUpdateDestroyUploadedFileAPI.as_view(),
        name="exhibit_detail",
    ),
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
