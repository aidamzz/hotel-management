from django.db import connection, transaction

from .models import Booking, Room


class NoRoomAvailable(Exception):
    """No room with the requested features is free for the stay."""


def book_room(*, user_identifier, beds, view, check_in, check_out):
    """Assign the lowest-id free room that matches beds and view.

    Stays are half-open: a booking occupies [check_in, check_out). A later
    stay may start at the earlier stay's check-out instant.

    Candidate rooms are locked for the duration of the transaction so two
    concurrent requests cannot take the same room. Databases that support
    SELECT FOR UPDATE lock those rows. SQLite does not, and instead reserves
    its write lock at the start of the transaction (transaction_mode=IMMEDIATE).
    """
    with transaction.atomic():
        candidates = Room.objects.filter(beds=beds, view=view).order_by("id")
        if connection.features.has_select_for_update:
            candidates = candidates.select_for_update()

        for room in candidates:
            overlap = room.bookings.filter(
                check_in__lt=check_out,
                check_out__gt=check_in,
            ).exists()
            if not overlap:
                return Booking.objects.create(
                    room=room,
                    user_identifier=user_identifier,
                    check_in=check_in,
                    check_out=check_out,
                )

    raise NoRoomAvailable
