from django.db import IntegrityError, connection, transaction

from .models import Booking, Room


class NoRoomAvailable(Exception):
    """No room with the requested features is free for the stay."""


def _locked_matches(beds, view):
    candidates = Room.objects.filter(beds=beds, view=view).order_by("id")
    if connection.features.has_select_for_update:
        candidates = candidates.select_for_update()
    return list(candidates)


def _overlaps(room, check_in, check_out, *, ignore_booking_id=None):
    bookings = room.bookings.filter(
        check_in__lt=check_out,
        check_out__gt=check_in,
    )
    if ignore_booking_id is not None:
        bookings = bookings.exclude(pk=ignore_booking_id)
    return bookings.exists()


def _assign(booking, room):
    booking.room = room
    try:
        with transaction.atomic():
            booking.save()
    except IntegrityError:
        return False
    return True


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
        for room in _locked_matches(beds, view):
            if _overlaps(room, check_in, check_out):
                continue
            booking = Booking(
                room=room,
                user_identifier=user_identifier,
                check_in=check_in,
                check_out=check_out,
            )
            if _assign(booking, room):
                return booking

    raise NoRoomAvailable


def update_booking(booking_id, *, user_identifier, beds, view, check_in, check_out):
    """Keep the booking's room when it still matches, otherwise move it.

    The current room stays assigned when its features equal the new request
    and no other stay on that room overlaps the new dates. Otherwise the
    lowest-id free match is chosen. This booking is ignored in the overlap
    check so its own current stay is not treated as a conflict.
    """
    with transaction.atomic():
        booking = (
            Booking.objects.select_for_update()
            .select_related("room")
            .get(pk=booking_id)
        )
        booking.user_identifier = user_identifier
        booking.check_in = check_in
        booking.check_out = check_out

        matches = _locked_matches(beds, view)
        current = booking.room
        if current.beds == beds and current.view == view:
            rooms = [current] + [room for room in matches if room.pk != current.pk]
        else:
            rooms = matches

        for room in rooms:
            if _overlaps(room, check_in, check_out, ignore_booking_id=booking.pk):
                continue
            if _assign(booking, room):
                return booking

    raise NoRoomAvailable
