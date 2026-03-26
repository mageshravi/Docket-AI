import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from events.api.serializers import (
    TimelineCreateSerializer,
    TimelineEventSerializer,
    TimelineSerializer,
)
from events.models import Timeline
from events.tasks import start_timeline_processing
from poc.models import Case


class ListCreateTimelineAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineCreateSerializer

    def _get_case(self):
        case_uuid = self.request.query_params.get("case")
        if case_uuid is None:
            return None

        try:
            uuid.UUID(case_uuid, version=4)
        except ValueError:
            return None

        try:
            return Case.objects.get(uuid=case_uuid)
        except Case.DoesNotExist:
            return Case.objects.none()

    def get_queryset(self):
        queryset = Timeline.objects.filter(created_by=self.request.user)

        case = self._get_case()
        if case:
            queryset = queryset.filter(case=case)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()

        if self.request.method == "POST":
            case_uuid = self.request.data.get("case")
            if case_uuid:
                case = get_object_or_404(Case, uuid=case_uuid)
                context["case"] = case

        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            self.perform_create(serializer)
            timeline = serializer.instance
            transaction.on_commit(lambda: start_timeline_processing.delay(timeline.id))

        return Response(
            TimelineSerializer(timeline).data, status=status.HTTP_201_CREATED
        )


class RetrieveTimelineAPI(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineSerializer

    def get_queryset(self):
        return Timeline.objects.filter(created_by=self.request.user)

    def get_object(self):
        timeline_id = self.kwargs.get("timeline_id")
        return get_object_or_404(self.get_queryset(), id=timeline_id)


class ListTimelineEventsAPI(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineEventSerializer

    def get_queryset(self):
        timeline_id = self.kwargs.get("timeline_id")
        timeline = get_object_or_404(Timeline, id=timeline_id)
        return timeline.events.all()
