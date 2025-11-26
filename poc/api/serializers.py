from rest_framework.serializers import ModelSerializer

from poc.models import Case, ChatMessage, ChatThread, Litigant, UploadedFile

__all__ = [
    "LitigantSerializer",
    "CaseSerializer",
    "UploadedFileSerializer",
    "ChatThreadSerializer",
]


class LitigantSerializer(ModelSerializer):
    class Meta:
        model = Litigant
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )


class CaseSerializer(ModelSerializer):
    class Meta:
        model = Case
        exclude = ("litigants",)
        read_only_fields = (
            "uuid",
            "created_at",
            "updated_at",
        )


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

    def create(self, validated_data):
        uploaded_file = validated_data.get("file")
        if uploaded_file:
            validated_data["filename"] = uploaded_file.name

        return super().create(validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["case"] = str(instance.case.uuid) if instance.case else None
        return representation


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
