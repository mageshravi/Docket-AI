from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from events.api.serializers import (
    TimelineCreateSerializer,
    TimelineEventSerializer,
    TimelineSerializer,
)
from events.models import Timeline, TimelineEvent
from events.tasks import start_timeline_processing
from poc.models import Case


class ListCreateTimelineAPI(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineCreateSerializer

    def _get_case_id_from_query_params(self):
        case_id = self.request.query_params.get("case")
        if case_id is None:
            return None

        try:
            return int(case_id)
        except (TypeError, ValueError):
            raise ValidationError({"case": "A valid integer is required."})

    def get_queryset(self):
        queryset = Timeline.objects.filter(created_by=self.request.user)

        case_id = self._get_case_id_from_query_params()
        if case_id is not None:
            queryset = queryset.filter(case_id=case_id)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()

        if self.request.method == "POST":
            case_id = self.request.data.get("case")
            if case_id:
                case = get_object_or_404(Case, id=case_id)
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


class ListTimelineEventAPI(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineEventSerializer

    def get_queryset(self):
        timeline_id = self.kwargs["timeline_id"]
        get_object_or_404(Timeline, id=timeline_id)
        return TimelineEvent.objects.filter(timeline_id=timeline_id)
