from rest_framework.serializers import ModelSerializer

from poc.models import ChatMessage, ChatThread, UploadedFile

__all__ = [
    "UploadedFileSerializer",
    "ChatThreadSerializer",
]


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


class ChatThreadSerializer(ModelSerializer):
    class Meta:
        model = ChatThread
        fields = "__all__"
        read_only_fields = (
            "uuid",
            "created_at",
            "updated_at",
        )


class ChatMessageSerializer(ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = "__all__"
        read_only_fields = (
            "thread",
            "role",
            "created_at",
            "updated_at",
        )
