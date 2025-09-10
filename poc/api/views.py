from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from poc.api.serializers import (
    ChatMessageSerializer,
    ChatThreadSerializer,
    UploadedFileSerializer,
)
from poc.langchain.chat_agent import send_message
from poc.models import Case, ChatThread, UploadedFile

__all__ = [
    "ListCreateUploadedFileAPI",
    "ListCreateThreadAPI",
    "CreateMessageAPI",
]


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


class CreateMessageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # validate case and thread
        case_uuid = self.kwargs.get("case_uuid")
        thread_uuid = self.kwargs.get("thread_uuid")
        thread = get_object_or_404(ChatThread, uuid=thread_uuid, case__uuid=case_uuid)
        # validate message content
        ip_serializer = ChatMessageSerializer(
            data=request.data,
        )
        ip_serializer.is_valid(raise_exception=True)
        # call the chat agent
        messages = send_message(
            thread_id=thread.id, user_input=ip_serializer.validated_data.get("content")
        )
        op_serializer = ChatMessageSerializer(messages, many=True)
        return Response(op_serializer.data, status=201)
