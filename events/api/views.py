from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from events.api.serializers import TimelineCreateSerializer, TimelineSerializer
from events.tasks import start_timeline_processing
from poc.models import Case


class CreateTimelineAPI(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TimelineCreateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        case_id = self.request.data.get("case")
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
