from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from poc.api.serializers import (
    CaseCompactSerializer,
    CaseSerializer,
    ChatMessageSerializer,
    ChatThreadSerializer,
    LitigantSerializer,
    UploadedFileSerializer,
)
from poc.langchain.chat_agent import send_message
from poc.models import Case, ChatMessage, ChatThread, Litigant, UploadedFile

__all__ = [
    "ListCreateCaseAPI",
    "RetrieveCaseAPI",
    "ListCreateUploadedFileAPI",
    "RetrieveUploadedFileAPI",
    "ListCreateThreadAPI",
    "ListCreateMessageAPI",
    "ListCreateLitigantAPI",
    "RetrieveLitigantAPI",
]


class ListCreateCaseAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CaseSerializer

    def get_queryset(self):
        queryset = Case.objects.all().order_by("-id")

        # check for query param 'search'
        search = self.request.query_params.get("search")
        if search:
            if len(search.strip()) > 2:
                queryset = queryset.filter(
                    Q(title__icontains=search) | Q(case_number__istartswith=search)
                )
            else:
                queryset = queryset.none()

        return queryset


class RetrieveCaseAPI(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Case.objects.all()
    lookup_field = "uuid"
    lookup_url_kwarg = "case_uuid"
    serializer_class = CaseCompactSerializer


class ListCreateUploadedFileAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UploadedFileSerializer

    def get_queryset(self):
        case_uuid = self.kwargs.get("case_uuid")
        queryset = UploadedFile.objects.filter(case__uuid=case_uuid).order_by("-id")

        # check for query param 'search'
        search = self.request.query_params.get("search")
        if search:
            if len(search.strip()) > 2:
                queryset = queryset.filter(file__icontains=search)
            else:
                queryset = queryset.none()

        return queryset

    def perform_create(self, serializer):
        case_uuid = self.kwargs.get("case_uuid")
        case = get_object_or_404(Case, uuid=case_uuid)
        serializer.save(case=case)


class RetrieveUploadedFileAPI(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UploadedFileSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        case_uuid = self.kwargs.get("case_uuid")
        return UploadedFile.objects.filter(case__uuid=case_uuid)


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


class ListCreateMessageAPI(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()

        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None

        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)

    def get_queryset(self):
        case_uuid = self.kwargs.get("case_uuid")
        thread_uuid = self.kwargs.get("thread_uuid")
        return ChatMessage.objects.filter(
            thread__uuid=thread_uuid, thread__case__uuid=case_uuid
        ).order_by("-id")

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ChatMessageSerializer(queryset, many=True)
        return Response(serializer.data)

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


class ListCreateLitigantAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LitigantSerializer

    def get_queryset(self):
        # check for query param 'search'
        search = self.request.query_params.get("search")
        if search:
            if len(search.strip()) > 2:
                # search in name, bio, email and phone fields
                return Litigant.objects.filter(
                    Q(name__icontains=search)
                    | Q(bio__icontains=search)
                    | Q(email__icontains=search)
                    | Q(phone__icontains=search)
                ).order_by("-id")
            else:
                return Litigant.objects.none()

        return Litigant.objects.all().order_by("-id")


class RetrieveLitigantAPI(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LitigantSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        return Litigant.objects.all()
