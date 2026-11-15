from rest_framework import serializers

from .models import Booking, Room


class ViewField(serializers.ChoiceField):
    """Accept Sea / Mountain / Yard in any letter case."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.strip().lower()
        return super().to_internal_value(data)


class RoomSerializer(serializers.ModelSerializer):
    view = ViewField(choices=Room.View.choices)

    class Meta:
        model = Room
        fields = ["id", "label", "beds", "view"]


class BookingSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "user_identifier",
            "check_in",
            "check_out",
            "created_at",
            "room",
        ]


class BookingCreateSerializer(serializers.Serializer):
    user_identifier = serializers.CharField(max_length=255)
    beds = serializers.IntegerField(min_value=1, max_value=5)
    view = ViewField(choices=Room.View.choices)
    check_in = serializers.DateTimeField()
    check_out = serializers.DateTimeField()

    def validate(self, attrs):
        if attrs["check_out"] <= attrs["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "Check-out must be after check-in."}
            )
        return attrs

    def validate_user_identifier(self, value):
        if not value.strip():
            raise serializers.ValidationError("This field may not be blank.")
        return value.strip()
