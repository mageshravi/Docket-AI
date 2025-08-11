from rest_framework.serializers import ModelSerializer

from poc.models import UploadedFile


class UploadedFileSerializer(ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = "__all__"
        read_only_fields = (
            "status",
            "error_message",
            "created_at",
            "updated_at",
        )
