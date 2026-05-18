from django.urls import path

from litigants.api.views import ListCreateLitigantAPI, RetrieveLitigantAPI

app_name = "litigants"
urlpatterns = [
    path(
        "litigants/",
        ListCreateLitigantAPI.as_view(),
        name="list_create",
    ),
    path(
        "litigants/<int:id>/",
        RetrieveLitigantAPI.as_view(),
        name="retrieve",
    ),
]
