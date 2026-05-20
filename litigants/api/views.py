from django.db.models import Q
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from litigants.models import Litigant

from .serializers import LitigantSerializer

__all__ = [
    "ListCreateLitigantAPI",
    "RetrieveLitigantAPI",
]


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
