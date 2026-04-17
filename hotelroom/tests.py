from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Booking, Room, RoomRating


User = get_user_model()


class RoomRatingViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="guest@example.com",
            username="guest1",
            password="secret123!",
            first_name="Guest",
            last_name="User",
            contact="09171234567",
            address="Manila",
            gender="Male",
        )
        self.room = Room.objects.create(
            name="Suite Room",
            room_number="101",
            room_type="suite",
            price_per_night=5000,
            capacity=2,
            max_bookings=1,
            description="A comfortable suite.",
            amenities=[],
            image_url="",
            status="available",
            floor=1,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today() - timedelta(days=3),
            check_out=date.today() - timedelta(days=1),
            guests=2,
            meal_category="breakfast",
            total_price=10000,
            status="completed",
        )
        self.second_booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today() - timedelta(days=6),
            check_out=date.today() - timedelta(days=4),
            guests=2,
            meal_category="breakfast",
            total_price=10000,
            status="completed",
        )
        self.client.force_authenticate(user=self.user)

    def test_rating_post_requires_explicit_booking_id(self):
        url = reverse("room-ratings", kwargs={"room_id": self.room.id})
        res = self.client.post(url, {"stars": 5, "comment": "Great stay!"}, format="json")

        self.assertEqual(res.status_code, 400)
        self.assertIn("booking_id", res.data["error"])
        self.assertEqual(RoomRating.objects.count(), 0)

    def test_rating_post_creates_review_for_selected_booking(self):
        url = reverse("room-ratings", kwargs={"room_id": self.room.id})
        res = self.client.post(
            url,
            {"booking_id": self.booking.id, "stars": 5, "comment": "Great stay!"},
            format="json",
        )

        self.assertEqual(res.status_code, 201)
        self.assertEqual(RoomRating.objects.count(), 1)
        rating = RoomRating.objects.get()
        self.assertEqual(rating.booking_id, self.booking.id)
        self.assertEqual(rating.room_id, self.room.id)

    def test_rating_post_updates_existing_review_for_same_booking(self):
        url = reverse("room-ratings", kwargs={"room_id": self.room.id})
        first = self.client.post(
            url,
            {"booking_id": self.booking.id, "stars": 4, "comment": "Nice stay."},
            format="json",
        )
        second = self.client.post(
            url,
            {"booking_id": self.booking.id, "stars": 5, "comment": "Even better the second time."},
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(RoomRating.objects.count(), 1)
        rating = RoomRating.objects.get()
        self.assertEqual(rating.stars, 5)
        self.assertEqual(rating.comment, "Even better the second time.")

    def test_rating_post_updates_existing_review_for_same_room_across_bookings(self):
        url = reverse("room-ratings", kwargs={"room_id": self.room.id})
        first = self.client.post(
            url,
            {"booking_id": self.booking.id, "stars": 4, "comment": "Nice stay."},
            format="json",
        )
        second = self.client.post(
            url,
            {"booking_id": self.second_booking.id, "stars": 5, "comment": "Second stay."},
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(RoomRating.objects.count(), 1)
        rating = RoomRating.objects.get()
        self.assertEqual(rating.booking_id, self.second_booking.id)
        self.assertEqual(rating.room_id, self.room.id)
        self.assertEqual(rating.stars, 5)


class BookingCancellationFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="guest2@example.com",
            username="guest2",
            password="secret123!",
            first_name="Guest",
            last_name="Two",
            contact="09170000000",
            address="Cebu",
            gender="Female",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin1",
            password="secret123!",
            first_name="Admin",
            last_name="User",
            role="admin",
        )
        self.room = Room.objects.create(
            name="Deluxe Room",
            room_number="202",
            room_type="deluxe",
            price_per_night=6000,
            capacity=2,
            max_bookings=1,
            description="A deluxe room.",
            amenities=[],
            image_url="",
            status="available",
            floor=2,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=4),
            guests=2,
            meal_category="breakfast",
            total_price=12000,
            status="confirmed",
        )

    def test_user_can_request_cancellation_with_comment(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("booking-detail", kwargs={"pk": self.booking.id})
        res = self.client.delete(url, {"reason": "Change of plans."}, format="json")

        self.assertEqual(res.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.cancel_request_status, "requested")
        self.assertEqual(self.booking.cancel_request_reason, "Change of plans.")
        self.assertEqual(self.booking.status, "confirmed")

    def test_admin_can_approve_pending_cancellation(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("booking-detail", kwargs={"pk": self.booking.id})
        res = self.client.delete(url, {"reason": "Need to cancel."}, format="json")
        self.assertEqual(res.status_code, 200)

        self.client.force_authenticate(user=self.admin)
        admin_url = reverse("admin-booking-detail", kwargs={"pk": self.booking.id})
        approve = self.client.patch(admin_url, {"cancel_action": "approve"}, format="json")

        self.assertEqual(approve.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "cancelled")
        self.assertEqual(self.booking.cancel_request_status, "approved")
        self.assertEqual(self.booking.cancel_reviewed_by_id, self.admin.id)


class BookingCheckInOutFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="guest3@example.com",
            username="guest3",
            password="secret123!",
            first_name="Guest",
            last_name="Three",
            contact="09173333333",
            address="Davao",
            gender="Male",
        )
        self.room = Room.objects.create(
            name="Family Room",
            room_number="303",
            room_type="family",
            price_per_night=7000,
            capacity=4,
            max_bookings=1,
            description="A family room.",
            amenities=[],
            image_url="",
            status="available",
            floor=3,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today() - timedelta(days=2),
            check_out=date.today() - timedelta(days=1),
            guests=3,
            meal_category="breakfast",
            total_price=7000,
            status="confirmed",
        )
        self.client.force_authenticate(user=self.user)

    def test_user_can_check_in_and_check_out_from_booking_details(self):
        url = reverse("booking-detail", kwargs={"pk": self.booking.id})

        check_in = self.client.patch(url, {"action": "check_in"}, format="json")
        self.assertEqual(check_in.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "checked_in")

        check_out = self.client.patch(url, {"action": "check_out"}, format="json")
        self.assertEqual(check_out.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "checked_out")


class BookingApprovalInventoryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="guest4@example.com",
            username="guest4",
            password="secret123!",
            first_name="Guest",
            last_name="Four",
            contact="09174444444",
            address="Iloilo",
            gender="Female",
        )
        self.admin = User.objects.create_user(
            email="admin2@example.com",
            username="admin2",
            password="secret123!",
            first_name="Admin",
            last_name="Two",
            role="admin",
        )
        self.room = Room.objects.create(
            name="Deluxe Room",
            room_number="404",
            room_type="deluxe",
            price_per_night=8000,
            capacity=2,
            max_bookings=1,
            description="A deluxe room.",
            amenities=[],
            image_url="",
            status="available",
            floor=4,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=4),
            guests=2,
            meal_category="breakfast",
            total_price=16000,
            status="pending",
        )

    def test_pending_booking_does_not_consume_room_until_confirmed(self):
        self.room.refresh_from_db()
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, "pending")
        self.assertEqual(self.room.status, "available")

        self.client.force_authenticate(user=self.admin)
        admin_url = reverse("admin-booking-detail", kwargs={"pk": self.booking.id})

        confirm = self.client.patch(admin_url, {"status": "confirmed"}, format="json")
        self.assertEqual(confirm.status_code, 200)

        self.room.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "confirmed")
        self.assertEqual(self.room.status, "occupied")

        checkout = self.client.patch(admin_url, {"status": "checked_out"}, format="json")
        self.assertEqual(checkout.status_code, 200)

        self.room.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "checked_out")
        self.assertEqual(self.room.status, "available")
