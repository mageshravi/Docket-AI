from rest_framework.serializers import (
    ModelSerializer,
    ValidationError,
)

from poc.models import (
    ChatMessage,
    ChatThread,
    UploadedFile,
)

__all__ = [
    "UploadedFileSerializer",
    "ChatThreadSerializer",
]


class UploadedFileSerializer(ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = "__all__"
        read_only_fields = (
            "case",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        # 1. Get 'case' from context
        case = self.context.get("case")
        if not case:
            raise ValidationError("Case context is required.")

        # 2. Check exhibit_code uniqueness within the case
        exhibit_code = attrs.get("exhibit_code")
        if exhibit_code:
            if UploadedFile.objects.filter(
                case=case, exhibit_code=exhibit_code
            ).exists():
                raise ValidationError(
                    {"exhibit_code": "This exhibit code is already used in this case."}
                )

        return attrs

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
