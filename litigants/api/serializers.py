from rest_framework.serializers import ModelSerializer

from litigants.models import Litigant, LitigantRole


class LitigantRoleSerializer(ModelSerializer):
    class Meta:
        model = LitigantRole
        exclude = (
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class LitigantSerializer(ModelSerializer):
    class Meta:
        model = Litigant
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )
