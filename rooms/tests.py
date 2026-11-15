from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Booking, Room


class RoomApiTests(APITestCase):
    def test_create_list_retrieve_update_and_delete_room(self):
        create = self.client.post(
            "/api/rooms/",
            {"label": "101", "beds": 2, "view": "Sea"},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        room_id = create.data["id"]
        self.assertEqual(create.data["label"], "101")
        self.assertEqual(create.data["beds"], 2)
        self.assertEqual(create.data["view"], "sea")

        listing = self.client.get("/api/rooms/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data), 1)

        detail = self.client.get(f"/api/rooms/{room_id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["label"], "101")

        updated = self.client.put(
            f"/api/rooms/{room_id}/",
            {"label": "102", "beds": 3, "view": "mountain"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["label"], "102")
        self.assertEqual(updated.data["beds"], 3)
        self.assertEqual(updated.data["view"], "mountain")

        patched = self.client.patch(
            f"/api/rooms/{room_id}/",
            {"view": "Yard"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["view"], "yard")

        deleted = self.client.delete(f"/api/rooms/{room_id}/")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        missing = self.client.get(f"/api/rooms/{room_id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

    def test_rejects_invalid_beds_view_and_duplicate_label(self):
        first = self.client.post(
            "/api/rooms/",
            {"label": "201", "beds": 1, "view": "yard"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        for beds in (0, 6):
            response = self.client.post(
                "/api/rooms/",
                {"label": f"beds-{beds}", "beds": beds, "view": "sea"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("beds", response.data)

        bad_view = self.client.post(
            "/api/rooms/",
            {"label": "202", "beds": 2, "view": "city"},
            format="json",
        )
        self.assertEqual(bad_view.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("view", bad_view.data)

        duplicate = self.client.post(
            "/api/rooms/",
            {"label": "201", "beds": 4, "view": "sea"},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("label", duplicate.data)

    def test_delete_room_with_booking_is_conflict(self):
        room = Room.objects.create(label="301", beds=1, view=Room.View.YARD)
        self._book(beds=1, view="yard")
        response = self.client.delete(f"/api/rooms/{room.id}/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Room.objects.filter(pk=room.id).exists())

    def _book(self, **overrides):
        payload = {
            "user_identifier": "guest-1",
            "beds": 2,
            "view": "sea",
            "check_in": "2026-12-01T15:00:00Z",
            "check_out": "2026-12-05T11:00:00Z",
        }
        payload.update(overrides)
        return self.client.post("/api/bookings/", payload, format="json")


class BookingApiTests(APITestCase):
    def setUp(self):
        self.sea_small = Room.objects.create(label="A", beds=2, view=Room.View.SEA)
        self.sea_small_later = Room.objects.create(
            label="B", beds=2, view=Room.View.SEA
        )
        Room.objects.create(label="C", beds=3, view=Room.View.SEA)
        Room.objects.create(label="D", beds=2, view=Room.View.MOUNTAIN)

    def test_assigns_lowest_id_matching_room(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": " user-42 ",
                "beds": 2,
                "view": "Sea",
                "check_in": "2026-12-01T15:00:00Z",
                "check_out": "2026-12-05T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user_identifier"], "user-42")
        self.assertEqual(response.data["room"]["id"], self.sea_small.id)
        self.assertEqual(response.data["room"]["label"], "A")
        self.assertEqual(response.data["room"]["beds"], 2)
        self.assertEqual(response.data["room"]["view"], "sea")

        listed = self.client.get("/api/bookings/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data), 1)

        detail_url = reverse("booking-detail", args=[response.data["id"]])
        detail = self.client.get(detail_url)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["room"]["label"], "A")

    def test_overlapping_booking_uses_next_free_room(self):
        first = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-01T15:00:00Z",
                "check_out": "2026-12-05T11:00:00Z",
            },
            format="json",
        )
        second = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-2",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-04T15:00:00Z",
                "check_out": "2026-12-08T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data["room"]["id"], self.sea_small_later.id)

        third = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-3",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-04T18:00:00Z",
                "check_out": "2026-12-06T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(third.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Booking.objects.count(), 2)

    def test_touching_stays_can_share_a_room(self):
        first = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-01T15:00:00Z",
                "check_out": "2026-12-05T11:00:00Z",
            },
            format="json",
        )
        second = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-2",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-05T11:00:00Z",
                "check_out": "2026-12-07T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data["room"]["id"], self.sea_small.id)

    def test_rejects_checkout_that_is_not_after_checkin(self):
        equal = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-05T11:00:00Z",
                "check_out": "2026-12-05T11:00:00Z",
            },
            format="json",
        )
        reversed_stay = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 2,
                "view": "sea",
                "check_in": "2026-12-06T11:00:00Z",
                "check_out": "2026-12-05T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(equal.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reversed_stay.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Booking.objects.count(), 0)

    def test_no_matching_features_is_conflict(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 5,
                "view": "yard",
                "check_in": "2026-12-01T15:00:00Z",
                "check_out": "2026-12-02T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_does_not_assign_room_with_different_features(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "user_identifier": "user-1",
                "beds": 2,
                "view": "mountain",
                "check_in": "2026-12-01T15:00:00Z",
                "check_out": "2026-12-02T11:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["room"]["label"], "D")
