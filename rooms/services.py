from django.db import IntegrityError, connection, transaction

from .models import Booking, Room


class NoRoomAvailable(Exception):
    """No room with the requested features is free for the stay."""


def book_room(*, user_identifier, beds, view, check_in, check_out):
    """Assign the lowest-id free room that matches beds and view.

    Stays are half-open: a booking occupies [check_in, check_out). A later
    stay may start at the earlier stay's check-out instant.

    Matching rooms are locked in id order for the whole transaction. A second
    request for those rooms waits, then sees the committed booking and takes
    another room or fails. PostgreSQL enforces the same rule with an exclusion
    constraint, so an overlapping insert cannot commit even if the lock is
    bypassed. That conflict rolls back to a savepoint and the search continues.
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
            if overlap:
                continue
            try:
                with transaction.atomic():
                    return Booking.objects.create(
                        room=room,
                        user_identifier=user_identifier,
                        check_in=check_in,
                        check_out=check_out,
                    )
            except IntegrityError:
                continue

    raise NoRoomAvailable
