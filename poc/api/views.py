from rest_framework.generics import ListCreateAPIView

from poc.api.serializers import UploadedFileSerializer
from poc.models import UploadedFile


class UploadedFileCreateAPI(ListCreateAPIView):
    serializer_class = UploadedFileSerializer
    queryset = UploadedFile.objects.all().order_by("-id")
