from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework import status
from .models import Room, Booking, RoomRating, Payment, PromoCode
from .serializers import RoomSerializer, BookingSerializer, RoomRatingSerializer, PaymentSerializer, PromoCodeSerializer


def _is_admin_or_staff(user):
    return getattr(user, "role", None) in ("admin", "staff")


CHECK_IN_TIME_OPTIONS = {
    "2:00 AM": dt_time(2, 0),
    "2:00 PM": dt_time(14, 0),
}
CHECK_OUT_TIME_OPTIONS = {
    "12:00 AM": dt_time(0, 0),
    "12:00 PM": dt_time(12, 0),
}
DEFAULT_CHECK_IN_TIME = Booking.DEFAULT_CHECK_IN_TIME
DEFAULT_CHECK_OUT_TIME = Booking.DEFAULT_CHECK_OUT_TIME


def _parse_booking_time(value, *, kind):
    normalized = str(value or "").strip().upper()
    if kind == "check_in":
        if not normalized:
            return DEFAULT_CHECK_IN_TIME
        for label, parsed in CHECK_IN_TIME_OPTIONS.items():
            if normalized == label.upper():
                return parsed
        raise ValueError("Check-in time must be 2:00 AM or 2:00 PM.")

    if not normalized:
        return DEFAULT_CHECK_OUT_TIME
    for label, parsed in CHECK_OUT_TIME_OPTIONS.items():
        if normalized == label.upper():
            return parsed
    raise ValueError("Check-out time must be 12:00 AM or 12:00 PM.")


def _format_booking_time(value):
    return value.strftime("%I:%M %p").lstrip("0")


def _booking_check_in_dt(booking):
    selected_time = booking.check_in_time or DEFAULT_CHECK_IN_TIME
    return timezone.make_aware(datetime.combine(booking.check_in, selected_time))


def _booking_check_out_dt(booking):
    selected_time = booking.check_out_time or DEFAULT_CHECK_OUT_TIME
    return timezone.make_aware(datetime.combine(booking.check_out, selected_time))


def _sync_completed_bookings():
    expired_bookings = list(
        Booking.objects.select_related("room").filter(
            status__in=("pending", "confirmed"),
            check_out__lte=date.today(),
        )
    )
    if not expired_bookings:
        return

    Booking.objects.filter(pk__in=[booking.pk for booking in expired_bookings]).update(status="completed")
    for booking in expired_bookings:
        booking.room.sync_status()


def _room_serializer(instance, *, many=False, request=None, **kwargs):
    context = kwargs.pop("context", {})
    if request is not None:
        context = {**context, "request": request}
    return RoomSerializer(instance, many=many, context=context, **kwargs)


class RoomListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _sync_completed_bookings()
        rooms = Room.objects.all()
        room_type   = request.query_params.get("type")
        capacity    = request.query_params.get("capacity")
        min_price   = request.query_params.get("min_price")
        max_price   = request.query_params.get("max_price")
        room_status = request.query_params.get("status")
        check_in    = request.query_params.get("check_in")
        check_out   = request.query_params.get("check_out")

        if room_status:
            rooms = rooms.filter(status=room_status)
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        if capacity:
            rooms = rooms.filter(capacity__gte=int(capacity))
        if min_price:
            rooms = rooms.filter(price_per_night__gte=min_price)
        if max_price:
            rooms = rooms.filter(price_per_night__lte=max_price)

        # Date-based availability: exclude rooms fully booked for the requested range
        if check_in and check_out:
            try:
                ci = date.fromisoformat(check_in)
                co = date.fromisoformat(check_out)
                unavailable_ids = []
                for room in rooms:
                    overlap = Booking.objects.filter(
                        room=room,
                        status__in=("pending", "confirmed", "checked_in"),
                        check_in__lt=co,
                        check_out__gt=ci,
                    ).count()
                    if overlap >= room.get_booking_limit():
                        unavailable_ids.append(room.id)
                rooms = rooms.exclude(id__in=unavailable_ids)
            except ValueError:
                pass

        return Response(_room_serializer(rooms, many=True, request=request).data)


class RoomDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        _sync_completed_bookings()
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        data = _room_serializer(room, request=request).data
        active_bookings = Booking.objects.filter(
            room=room, status__in=("pending", "confirmed", "checked_in"),
        ).values("check_in", "check_out")
        data["booked_ranges"] = [
            {"check_in": str(b["check_in"]), "check_out": str(b["check_out"])}
            for b in active_bookings
        ]
        data["max_bookings"] = room.get_booking_limit()
        return Response(data)


class AdminRoomView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        if not _is_admin_or_staff(request.user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        rooms = Room.objects.all().order_by("room_number")
        return Response(_room_serializer(rooms, many=True, request=request).data)

    def post(self, request):
        if not _is_admin_or_staff(request.user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = _room_serializer(None, request=request, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        if not _is_admin_or_staff(request.user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = _room_serializer(room, request=request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            Room.objects.get(pk=pk).delete()
        except Room.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Deleted"}, status=status.HTTP_204_NO_CONTENT)


class PromoCodeValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").strip().upper()
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
        except PromoCode.DoesNotExist:
            return Response({"error": "Invalid or expired promo code."}, status=status.HTTP_400_BAD_REQUEST)
        if promo.times_used >= promo.max_uses:
            return Response({"error": "This promo code has reached its usage limit."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"code": promo.code, "discount_percent": promo.discount_percent})


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            room_id = int(request.data.get("room"))
            room    = Room.objects.get(pk=room_id)
        except (TypeError, ValueError):
            return Response({"error": "Invalid room id."}, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({"error": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

        # Sync room status before checking availability
        room.sync_status()
        
        if room.status == "maintenance":
            return Response({"error": "This room is under maintenance and cannot be booked."}, status=status.HTTP_400_BAD_REQUEST)
        
        if room.status == "occupied":
            return Response({"error": "This room is fully booked and not available for new reservations. Please choose another room or different dates."}, status=status.HTTP_400_BAD_REQUEST)

        check_in_str  = request.data.get("check_in")
        check_out_str = request.data.get("check_out")
        check_in_time_str = request.data.get("check_in_time")
        check_out_time_str = request.data.get("check_out_time")
        guests        = int(request.data.get("guests", 1))
        meal_category = str(request.data.get("meal_category", "breakfast")).strip().lower()
        special       = request.data.get("special_requests", "")
        promo_input   = request.data.get("promo_code", "").strip().upper()
        pay_method    = request.data.get("payment_method", "cash")
        pay_reference = request.data.get("payment_reference", "")

        if not check_in_str or not check_out_str:
            return Response({"error": "Check-in and check-out dates are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ci = date.fromisoformat(check_in_str)
            co = date.fromisoformat(check_out_str)
        except ValueError:
            return Response({"error": "Use date format YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            check_in_time = _parse_booking_time(check_in_time_str, kind="check_in")
            check_out_time = _parse_booking_time(check_out_time_str, kind="check_out")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if co <= ci:
            return Response({"error": "Check-out must be after check-in."}, status=status.HTTP_400_BAD_REQUEST)
        if ci < date.today():
            return Response({"error": "Check-in date cannot be in the past."}, status=status.HTTP_400_BAD_REQUEST)
        if guests > room.capacity:
            return Response({"error": f"Room capacity is {room.capacity} guests."}, status=status.HTTP_400_BAD_REQUEST)
        if meal_category not in dict(Booking.MEAL_CATEGORY_CHOICES):
            return Response({"error": "Meal category must be breakfast, lunch, dinner, or both."}, status=status.HTTP_400_BAD_REQUEST)

        overlapping = Booking.objects.filter(
            room=room, status__in=("pending", "confirmed", "checked_in"),
            check_in__lt=co, check_out__gt=ci,
        ).count()
        if overlapping >= room.get_booking_limit():
            return Response({"error": "This room is fully booked for the selected dates. Please choose different dates or another room. You can only proceed with booking once existing guests have checked out."}, status=status.HTTP_400_BAD_REQUEST)

        nights      = (co - ci).days
        base_price  = nights * room.price_per_night
        free_food_guests = min(guests, room.free_food_guest_limit)
        extra_guest_count = max(guests - room.free_food_guest_limit, 0)
        extra_guest_fee_total = Decimal(str(extra_guest_count)) * room.extra_guest_fee_per_night * nights
        meal_addon_rate = room.get_meal_rate(meal_category, extra_guest=False)
        extra_meal_rate = room.get_meal_rate(meal_category, extra_guest=True)
        meal_addon_total = (
            Decimal(str(free_food_guests)) * meal_addon_rate * nights
            + Decimal(str(extra_guest_count)) * extra_meal_rate * nights
        )
        discount    = Decimal("0")
        promo_code  = ""

        if promo_input:
            try:
                promo = PromoCode.objects.get(code=promo_input, is_active=True)
                if promo.times_used < promo.max_uses:
                    discount   = ((base_price + extra_guest_fee_total + meal_addon_total) * promo.discount_percent) / 100
                    promo_code = promo.code
                    promo.times_used += 1
                    promo.save()
            except PromoCode.DoesNotExist:
                pass

        total_price = base_price + extra_guest_fee_total + meal_addon_total - discount

        booking = Booking.objects.create(
            user=request.user,
            room=room,
            check_in=ci,
            check_out=co,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            guests=guests,
            meal_category=meal_category,
            total_price=total_price,
            status="pending",
            special_requests=special,
            promo_code=promo_code,
            discount_amount=discount,
            free_food_guests=free_food_guests,
            extra_guest_count=extra_guest_count,
            extra_guest_fee_per_night=room.extra_guest_fee_per_night,
            extra_guest_fee_total=extra_guest_fee_total,
            meal_addon_rate=meal_addon_rate,
            meal_addon_total=meal_addon_total,
        )
        payment_reference = pay_reference.strip() or booking.reference_number or ""
        if pay_method == "cash" and not pay_reference.strip():
            payment_reference = booking.reference_number or ""
        sent_amount_value = request.data.get("payment_amount", "").strip()
        sent_amount = None
        if sent_amount_value:
            try:
                sent_amount = Decimal(sent_amount_value)
            except Exception:
                return Response({"error": "Enter a valid payment amount."}, status=status.HTTP_400_BAD_REQUEST)
            if sent_amount <= 0:
                return Response({"error": "Payment amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
        elif pay_method == "gcash":
            return Response({"error": "Please enter the amount you sent via GCash."}, status=status.HTTP_400_BAD_REQUEST)

        # Create payment record
        Payment.objects.create(
            booking=booking,
            method=pay_method,
            reference_number=payment_reference,
            amount=total_price,
            sent_amount=sent_amount,
            status="pending" if pay_method == "cash" else "paid",
        )


        # Keep the booking pending until staff reviews it in the dashboard.

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _sync_completed_bookings()
        bookings = Booking.objects.filter(user=request.user).order_by("-created_at")
        return Response(BookingSerializer(bookings, many=True).data)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _request_cancellation(self, request, booking):
        if booking.status in ("cancelled", "completed", "checked_in", "checked_out"):
            return Response(
                {"error": "This booking can no longer be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = str(
            request.data.get("reason")
            or request.data.get("comment")
            or request.data.get("cancel_reason")
            or ""
        ).strip()
        if not reason:
            return Response(
                {"error": "Please add a cancellation comment before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.cancel_request_status = "requested"
        booking.cancel_request_reason = reason
        booking.cancel_requested_at = timezone.now()
        booking.cancel_reviewed_at = None
        booking.cancel_reviewed_by = None
        booking.save()
        return Response(
            {
                "message": "Cancellation request submitted.",
                "booking": BookingSerializer(booking).data,
            }
        )

    def _change_status(self, request, booking, action):
        if booking.cancel_request_status == "requested":
            return Response(
                {"error": "Resolve the pending cancellation request first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "check_in":
            if booking.status != "confirmed":
                return Response(
                    {"error": "Only confirmed bookings can be checked in."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.now() < _booking_check_in_dt(booking):
                return Response(
                    {"error": f"Check-in is only available on or after {booking.check_in} at {_format_booking_time(booking.check_in_time or DEFAULT_CHECK_IN_TIME)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            booking.status = "checked_in"
        elif action == "check_out":
            if booking.status != "checked_in":
                return Response(
                    {"error": "Only checked-in bookings can be checked out."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.now() < _booking_check_out_dt(booking):
                return Response(
                    {"error": f"Check-out is only available on or after {booking.check_out} at {_format_booking_time(booking.check_out_time or DEFAULT_CHECK_OUT_TIME)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            booking.status = "checked_out"
        else:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        booking.save()
        return Response(
            {
                "message": "Booking status updated.",
                "booking": BookingSerializer(booking).data,
            }
        )

    def _extend_stay(self, request, booking):
        if booking.status != "checked_in":
            return Response(
                {"error": "Only checked-in bookings can be extended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > _booking_check_out_dt(booking):
            return Response(
                {"error": "This stay has already passed the checkout date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            extend_days = int(request.data.get("extend_days", 1))
        except (TypeError, ValueError):
            return Response(
                {"error": "Extension days must be a valid number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if extend_days < 1 or extend_days > 7:
            return Response(
                {"error": "You can extend between 1 and 7 days at a time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_check_out = booking.check_out + timedelta(days=extend_days)
        overlapping = Booking.objects.filter(
            room=booking.room,
            status__in=("pending", "confirmed", "checked_in"),
            check_in__lt=new_check_out,
            check_out__gt=booking.check_out,
        ).exclude(pk=booking.pk).count()
        if overlapping >= booking.room.get_booking_limit():
            return Response(
                {"error": "This room is not available for the extra nights."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.check_out = new_check_out
        booking.save()
        return Response(
            {
                "message": "Booking extended successfully.",
                "booking": BookingSerializer(booking).data,
            }
        )

    def get(self, request, pk):
        _sync_completed_bookings()
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookingSerializer(booking).data)

    def patch(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action") or request.data.get("cancel_action") or "").strip().lower()
        if action in {"check_in", "check-out", "check_out"}:
            return self._change_status(request, booking, "check_out" if action in {"check-out", "check_out"} else "check_in")
        if action in {"extend_stay", "extend"}:
            return self._extend_stay(request, booking)
        if action not in {"request_cancellation", "cancel_request", "request_cancel"}:
            return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)
        return self._request_cancellation(request, booking)

    def delete(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)
        return self._request_cancellation(request, booking)


class AdminBookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        _sync_completed_bookings()
        bookings = Booking.objects.all().order_by("-created_at")
        return Response(BookingSerializer(bookings, many=True).data)


class AdminBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role not in ("admin", "staff"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        _sync_completed_bookings()
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        cancel_action = str(request.data.get("cancel_action") or "").strip().lower()
        if cancel_action:
            if booking.cancel_request_status != "requested":
                return Response({"error": "There is no pending cancellation request."}, status=status.HTTP_400_BAD_REQUEST)
            if cancel_action not in {"approve", "reject"}:
                return Response({"error": "Invalid cancellation action."}, status=status.HTTP_400_BAD_REQUEST)

            booking.cancel_reviewed_at = timezone.now()
            booking.cancel_reviewed_by = request.user
            if cancel_action == "approve":
                booking.status = "cancelled"
                booking.cancel_request_status = "approved"
            else:
                booking.cancel_request_status = "rejected"
            booking.save()
            return Response(BookingSerializer(booking).data)

        new_status = request.data.get("status")
        if new_status not in dict(Booking.STATUS_CHOICES):
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        if booking.cancel_request_status == "requested":
            return Response(
                {"error": "Resolve the pending cancellation request first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = new_status
        booking.save()
        return Response(BookingSerializer(booking).data)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        booking.delete()
        return Response({"message": "Deleted"}, status=status.HTTP_204_NO_CONTENT)


class RoomRatingView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _is_reviewable_status(status: str) -> bool:
        normalized = (status or "").strip().lower().replace("_", " ")
        return normalized in {"completed", "checked out", "checkout"}

    @staticmethod
    def _is_reviewable_booking(booking: Booking) -> bool:
        if RoomRatingView._is_reviewable_status(booking.status):
            return True
        return timezone.now() >= _booking_check_out_dt(booking)

    def get(self, request, room_id):
        _sync_completed_bookings()
        ratings = RoomRating.objects.filter(room_id=room_id)
        return Response(RoomRatingSerializer(ratings, many=True).data)

    def post(self, request, room_id):
        try:
            room = Room.objects.get(pk=room_id)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        stars      = request.data.get("stars")
        comment    = request.data.get("comment", "")
        booking_id = request.data.get("booking_id")

        try:
            stars_value = int(stars)
        except (TypeError, ValueError):
            return Response({"error": "Rating must be between 1 and 5"}, status=status.HTTP_400_BAD_REQUEST)

        if not (1 <= stars_value <= 5):
            return Response({"error": "Rating must be between 1 and 5"}, status=status.HTTP_400_BAD_REQUEST)

        eligible_bookings = Booking.objects.filter(
            user=request.user,
            room=room,
        ).order_by("-created_at")

        eligible_bookings = [b for b in eligible_bookings if self._is_reviewable_booking(b)]

        if not eligible_bookings:
            return Response({"error": "You can only rate rooms you have booked"}, status=status.HTTP_403_FORBIDDEN)

        if not booking_id:
            return Response(
                {"error": "booking_id is required so your review is attached to the correct stay."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking_obj = next(b for b in eligible_bookings if b.pk == int(booking_id))
        except (StopIteration, TypeError, ValueError):
            return Response({"error": "Booking not found for this room."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            rating_qs = RoomRating.objects.select_for_update().filter(
                user=request.user,
                room=room,
            ).order_by("-created_at", "-id")
            rating = rating_qs.first()
            created = rating is None

            if rating is None:
                rating = RoomRating(user=request.user, room=room)
            elif rating_qs.count() > 1:
                RoomRating.objects.filter(
                    user=request.user,
                    room=room,
                ).exclude(pk=rating.pk).delete()

            rating.user = request.user
            rating.room = room
            rating.booking = booking_obj
            rating.stars = stars_value
            rating.comment = comment
            rating.save()

        return Response(
            RoomRatingSerializer(rating).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyRoomRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ratings = RoomRating.objects.filter(user=request.user).select_related("room", "booking", "user")
        return Response(RoomRatingSerializer(ratings, many=True).data)


class AdminRoomRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin_or_staff(request.user):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        ratings = RoomRating.objects.select_related("room", "booking", "user").order_by("-created_at")
        return Response(RoomRatingSerializer(ratings, many=True).data)


class AdminPromoCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(PromoCodeSerializer(PromoCode.objects.all().order_by("-created_at"), many=True).data)

    def post(self, request):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        s = PromoCodeSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return Response(s.data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            promo = PromoCode.objects.get(pk=pk)
        except PromoCode.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        s = PromoCodeSerializer(promo, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if request.user.role != "admin":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            PromoCode.objects.get(pk=pk).delete()
        except PromoCode.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Deleted"}, status=status.HTTP_204_NO_CONTENT)
