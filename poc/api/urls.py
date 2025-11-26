from django.urls import path

from poc.api.views import (
    CaseDetailAPI,
    ListCreateLitigantAPI,
    ListCreateMessageAPI,
    ListCreateThreadAPI,
    ListCreateUploadedFileAPI,
    RetrieveUploadedFileAPI,
)

app_name = "poc"
urlpatterns = [
    path(
        "cases/<uuid:case_uuid>/exhibits/",
        ListCreateUploadedFileAPI.as_view(),
        name="exhibits",
    ),
    path(
        "cases/<uuid:case_uuid>/exhibits/<int:id>/",
        RetrieveUploadedFileAPI.as_view(),
        name="exhibit_detail",
    ),
    path("cases/<uuid:case_uuid>/", CaseDetailAPI.as_view(), name="case_detail"),
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
    path(
        "litigants/",
        ListCreateLitigantAPI.as_view(),
        name="litigants",
    ),
]
