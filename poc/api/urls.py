from django.urls import path

from poc.api.views import UploadedFileCreateAPI

app_name = "poc"
urlpatterns = [
    path("uploaded-files/", UploadedFileCreateAPI.as_view(), name="uploaded_files"),
]
