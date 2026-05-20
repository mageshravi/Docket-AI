from django.urls import path

from .views import ListCreateCaseAPI, RetrieveUpdateCaseAPI

app_name = "cases"
urlpatterns = [
    path("", ListCreateCaseAPI.as_view(), name="list"),
    path("<uuid:case_uuid>/", RetrieveUpdateCaseAPI.as_view(), name="detail"),
]
