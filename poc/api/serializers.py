from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    ValidationError,
)

from poc.models import (
    Case,
    CaseLitigant,
    ChatMessage,
    ChatThread,
    Litigant,
    LitigantRole,
    UploadedFile,
)

__all__ = [
    "LitigantSerializer",
    "CaseSerializer",
    "CaseCompactSerializer",
    "UploadedFileSerializer",
    "ChatThreadSerializer",
]


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


class CaseLitigantWriteSerializer(ModelSerializer):
    litigant = PrimaryKeyRelatedField(queryset=Litigant.objects.all(), write_only=True)
    role = PrimaryKeyRelatedField(queryset=LitigantRole.objects.all(), write_only=True)

    class Meta:
        model = CaseLitigant
        fields = ("litigant", "role", "is_our_client")


class CaseLitigantReadSerializer(ModelSerializer):
    litigant = LitigantSerializer(read_only=True)
    role = LitigantRoleSerializer(read_only=True)

    class Meta:
        model = CaseLitigant
        fields = ("litigant", "role", "is_our_client")


class CaseSerializer(ModelSerializer):
    # field for READING (Retrieve and List)
    case_litigants = CaseLitigantReadSerializer(
        many=True,
        read_only=True,
    )

    # field for WRITING (Create and Update)
    case_litigants_data = CaseLitigantWriteSerializer(
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Case
        fields = (
            "uuid",
            "title",
            "description",
            "case_number",
            "case_litigants",  # read-only field
            "case_litigants_data",  # write-only field
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "uuid",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        # 1. Extract case_litigants_data
        case_litigants_data = validated_data.pop("case_litigants_data", [])

        # 2. Create the Case instance
        case = Case.objects.create(**validated_data)

        # 3. Create CaseLitigant instances
        for litigant_data in case_litigants_data:
            CaseLitigant.objects.create(
                case=case,
                litigant=litigant_data["litigant"],
                role=litigant_data["role"],
                is_our_client=litigant_data.get("is_our_client", False),
            )

        # 4. Return the created Case instance
        return case


class CaseCompactSerializer(ModelSerializer):
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
