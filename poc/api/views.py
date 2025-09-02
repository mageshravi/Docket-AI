from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from poc.api.serializers import ChatThreadSerializer, UploadedFileSerializer
from poc.models import ChatThread, UploadedFile


class ListCreateUploadedFileAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UploadedFileSerializer
    queryset = UploadedFile.objects.all().order_by("-id")


class ListCreateThreadAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatThreadSerializer
    queryset = ChatThread.objects.all().order_by("-id")
