from django.db.models import Q
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from cases.models import Case

from .serializers import CaseCompactSerializer, CaseSerializer

__all__ = [
    "ListCreateCaseAPI",
    "RetrieveUpdateCaseAPI",
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
                    Q(title__icontains=search) | Q(case_number__icontains=search)
                )
            else:
                queryset = queryset.none()

        return queryset


class RetrieveUpdateCaseAPI(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "case_uuid"
    http_method_names = ["get", "patch", "options"]

    def get_queryset(self):
        if self.request.query_params.get("compact") == "true":
            return Case.objects.all()

        return Case.objects.prefetch_related(
            "case_litigants__litigant",
            "case_litigants__role",
        )

    def get_serializer_class(self):
        # check for query param 'compact'
        if self.request.query_params.get("compact") == "true":
            return CaseCompactSerializer

        # otherwise return full serializer
        return CaseSerializer
