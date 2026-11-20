from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Booking, Room
from .serializers import BookingCreateSerializer, BookingSerializer, RoomSerializer
from .services import NoRoomAvailable, book_room, update_booking


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "This room has bookings and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Booking.objects.select_related("room")
    serializer_class = BookingSerializer

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BookingCreateSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        incoming = BookingCreateSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        try:
            booking = book_room(**incoming.validated_data)
        except NoRoomAvailable:
            return Response(
                {
                    "detail": (
                        "No available room matches the requested features "
                        "for those dates."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        body = BookingSerializer(booking)
        return Response(body.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        booking = self.get_object()
        partial = kwargs.pop("partial", False)
        incoming = BookingCreateSerializer(data=request.data, partial=partial)
        incoming.is_valid(raise_exception=True)
        data = incoming.validated_data
        check_in = data.get("check_in", booking.check_in)
        check_out = data.get("check_out", booking.check_out)
        if check_out <= check_in:
            raise ValidationError({"check_out": "Check-out must be after check-in."})
        try:
            booking = update_booking(
                booking.pk,
                user_identifier=data.get("user_identifier", booking.user_identifier),
                beds=data.get("beds", booking.room.beds),
                view=data.get("view", booking.room.view),
                check_in=check_in,
                check_out=check_out,
            )
        except NoRoomAvailable:
            return Response(
                {
                    "detail": (
                        "No available room matches the requested features "
                        "for those dates."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        body = BookingSerializer(booking)
        return Response(body.data, status=status.HTTP_200_OK)
