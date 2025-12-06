from django.urls import path

from poc.api.views import (
    ListCreateCaseAPI,
    ListCreateLitigantAPI,
    ListCreateMessageAPI,
    ListCreateThreadAPI,
    ListCreateUploadedFileAPI,
    RetrieveCaseAPI,
    RetrieveLitigantAPI,
    RetrieveUpdateUploadedFileAPI,
)

app_name = "poc"
urlpatterns = [
    path("cases/", ListCreateCaseAPI.as_view(), name="cases"),
    path("cases/<uuid:case_uuid>/", RetrieveCaseAPI.as_view(), name="case_detail"),
    path(
        "cases/<uuid:case_uuid>/exhibits/",
        ListCreateUploadedFileAPI.as_view(),
        name="exhibits",
    ),
    path(
        "cases/<uuid:case_uuid>/exhibits/<int:id>/",
        RetrieveUpdateUploadedFileAPI.as_view(),
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
    path(
        "litigants/",
        ListCreateLitigantAPI.as_view(),
        name="litigants",
    ),
    path(
        "litigants/<int:id>/",
        RetrieveLitigantAPI.as_view(),
        name="litigant_detail",
    ),
]
