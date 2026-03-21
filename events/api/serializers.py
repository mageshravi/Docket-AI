from rest_framework import serializers
from rest_framework.serializers import ValidationError

from events.models import Timeline, TimelineEvent, TimelineExhibit
from poc.models import UploadedFile


class TimelineCreateSerializer(serializers.ModelSerializer):
    case = serializers.IntegerField(write_only=True)
    exhibits = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_null=False,
        write_only=True,
    )

    class Meta:
        model = Timeline
        fields = (
            "id",
            "name",
            "case",
            "exhibits",
            "event_extraction_status",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "event_extraction_status",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        validators = []

    def validate_name(self, value):
        name = value.strip()
        if len(name) < 5:
            raise ValidationError("Timeline name must be at least 5 characters long.")

        if not name[0].isalpha():
            raise ValidationError("Timeline name must start with an alphabet.")

        return name

    def validate(self, attrs):
        case = self.context.get("case")

        if Timeline.objects.filter(case=case, name=attrs["name"]).exists():
            raise ValidationError({"name": "Name already exists."})

        exhibits_provided = "exhibits" in self.initial_data
        exhibit_ids = attrs.get("exhibits")

        if exhibits_provided and len(exhibit_ids) == 0:
            raise ValidationError(
                {"exhibits": "Exhibits list cannot be empty while creating timeline."}
            )

        if exhibits_provided:
            exhibits_queryset = UploadedFile.active_objects.filter(
                case=case,
                id__in=exhibit_ids,
            )

            if exhibits_queryset.count() != len(set(exhibit_ids)):
                raise ValidationError(
                    {"exhibits": "One or more exhibits are invalid for the given case."}
                )
        else:
            exhibits_queryset = UploadedFile.active_objects.filter(case=case)
            if not exhibits_queryset.exists():
                raise ValidationError(
                    {
                        "exhibits": "No exhibits are associated with this case to create timeline."
                    }
                )

        attrs["_resolved_exhibits"] = exhibits_queryset
        return attrs

    def create(self, validated_data):
        case = self.context["case"]
        user = self.context["request"].user
        exhibits = validated_data.pop("_resolved_exhibits")
        validated_data.pop("case", None)
        validated_data.pop("exhibits", None)

        timeline = Timeline.objects.create(
            case=case,
            created_by=user,
            **validated_data,
        )

        TimelineExhibit.objects.bulk_create(
            [
                TimelineExhibit(timeline=timeline, exhibit=exhibit)
                for exhibit in exhibits
            ]
        )

        return timeline


class TimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timeline
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "created_at",
            "updated_at",
        )


class TimelineEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineEvent
        fields = (
            "id",
            "title",
            "description",
            "event_date",
            "place",
        )
