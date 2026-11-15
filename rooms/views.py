from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .models import Booking, Room
from .serializers import BookingCreateSerializer, BookingSerializer, RoomSerializer
from .services import NoRoomAvailable, book_room


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
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Booking.objects.select_related("room")
    serializer_class = BookingSerializer

    def get_serializer_class(self):
        if self.action == "create":
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
