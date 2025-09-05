from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated

from poc.api.serializers import ChatThreadSerializer, UploadedFileSerializer
from poc.models import Case, ChatThread, UploadedFile


class ListCreateUploadedFileAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UploadedFileSerializer
    queryset = UploadedFile.objects.all().order_by("-id")


class ListCreateThreadAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatThreadSerializer

    def get_queryset(self):
        case_uuid = self.kwargs.get("case_uuid")
        return ChatThread.objects.filter(case__uuid=case_uuid).order_by("-id")

    def perform_create(self, serializer):
        case_uuid = self.kwargs.get("case_uuid")
        case = get_object_or_404(Case, uuid=case_uuid)
        serializer.save(case=case)
