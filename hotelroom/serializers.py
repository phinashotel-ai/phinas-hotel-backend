from rest_framework import serializers
from .models import Room, Booking, RoomRating, Payment, PromoCode
from django.db.models import Avg
from datetime import time as dt_time

CHECK_IN_TIME = dt_time(14, 0)
CHECK_OUT_TIME = dt_time(12, 0)


class RoomRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    room_name = serializers.CharField(source="room.name", read_only=True)
    room_number = serializers.CharField(source="room.room_number", read_only=True)

    class Meta:
        model  = RoomRating
        fields = ["id", "user", "user_name", "room", "room_name", "room_number", "booking", "stars", "comment", "created_at"]
        read_only_fields = ["user", "user_name", "room_name", "room_number", "created_at"]


class RoomSerializer(serializers.ModelSerializer):
    avg_rating   = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    current_bookings = serializers.SerializerMethodField()
    is_fully_booked = serializers.SerializerMethodField()

    class Meta:
        model  = Room
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if getattr(instance, "room_image", None):
            image_url = instance.room_image.url
            if request is not None:
                image_url = request.build_absolute_uri(image_url)
            data["image_url"] = image_url
        return data

    def validate_amenities(self, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        capacity = attrs.get("capacity")
        if capacity is None and self.instance is not None:
            capacity = self.instance.capacity
        if capacity is not None:
            attrs["max_bookings"] = max(1, int(capacity))
        return attrs

    def get_avg_rating(self, obj):
        avg = obj.ratings.aggregate(a=Avg("stars"))["a"]
        if not avg:
            return None
        normalized = avg / 2 if avg > 5 else avg
        return round(normalized, 1)

    def get_rating_count(self, obj):
        return obj.ratings.count()

    def get_current_bookings(self, obj):
        from datetime import date

        today = date.today()
        return obj.bookings.filter(
            status__in=("pending", "confirmed", "checked_in"),
            check_in__lte=today,
            check_out__gt=today,
        ).count()

    def get_is_fully_booked(self, obj):
        return self.get_current_bookings(obj) >= obj.get_booking_limit()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Payment
        fields = ["id", "booking", "method", "reference_number", "amount", "sent_amount", "status", "created_at"]
        read_only_fields = ["id", "amount", "created_at"]


class BookingSerializer(serializers.ModelSerializer):
    room_name    = serializers.CharField(source="room.name",        read_only=True)
    room_number  = serializers.CharField(source="room.room_number", read_only=True)
    room_type    = serializers.CharField(source="room.room_type",   read_only=True)
    user_name    = serializers.CharField(source="user.username",    read_only=True)
    user_email   = serializers.EmailField(source="user.email", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    payment      = PaymentSerializer(read_only=True)
    cancel_reviewed_by_name = serializers.CharField(source="cancel_reviewed_by.username", read_only=True, allow_null=True)
    check_in_time = serializers.SerializerMethodField()
    check_out_time = serializers.SerializerMethodField()
    check_in_at = serializers.SerializerMethodField()
    check_out_at = serializers.SerializerMethodField()

    class Meta:
        model  = Booking
        fields = [
            "id", "user", "room", "room_name", "room_number", "room_type", "user_name", "user_email", "user_first_name",
            "reference_number",
            "check_in", "check_out", "check_in_time", "check_out_time", "check_in_at", "check_out_at",
            "guests", "meal_category", "total_price", "status",
            "cancel_request_status", "cancel_request_reason", "cancel_requested_at",
            "cancel_reviewed_at", "cancel_reviewed_by_name",
            "special_requests", "promo_code", "discount_amount", "free_food_guests",
            "extra_guest_count", "extra_guest_fee_per_night", "extra_guest_fee_total",
            "meal_addon_rate", "meal_addon_total",
            "payment", "created_at",
        ]
        read_only_fields = [
            "user", "total_price", "status", "created_at",
            "room_name", "room_number", "room_type", "user_name", "user_email", "user_first_name", "payment", "reference_number",
            "cancel_request_status", "cancel_request_reason", "cancel_requested_at",
            "cancel_reviewed_at", "cancel_reviewed_by_name",
            "free_food_guests", "extra_guest_count", "extra_guest_fee_per_night", "extra_guest_fee_total",
            "meal_addon_rate", "meal_addon_total",
        ]

    def get_check_in_time(self, obj):
        return CHECK_IN_TIME.strftime("%I:%M %p").lstrip("0")

    def get_check_out_time(self, obj):
        return CHECK_OUT_TIME.strftime("%I:%M %p").lstrip("0")

    def get_check_in_at(self, obj):
        return f"{obj.check_in.isoformat()}T{CHECK_IN_TIME.strftime('%H:%M:%S')}"

    def get_check_out_at(self, obj):
        return f"{obj.check_out.isoformat()}T{CHECK_OUT_TIME.strftime('%H:%M:%S')}"

    def validate(self, data):
        check_in  = data.get("check_in")
        check_out = data.get("check_out")
        room      = data.get("room")
        guests    = data.get("guests", 1)

        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError("Check-out must be after check-in.")

        if room and guests > room.capacity:
            raise serializers.ValidationError(f"Room capacity is {room.capacity} guests.")

        if room and check_in and check_out:
            overlapping_count = Booking.objects.filter(
                room=room,
                status__in=("pending", "confirmed", "checked_in"),
                check_in__lt=check_out,
                check_out__gt=check_in,
            ).count()
            if overlapping_count >= room.get_booking_limit():
                raise serializers.ValidationError("This room is fully booked for the selected dates.")
        meal_category = data.get("meal_category")
        if meal_category and meal_category not in dict(Booking.MEAL_CATEGORY_CHOICES):
            raise serializers.ValidationError({"meal_category": "Choose breakfast, lunch, or dinner."})
        return data


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PromoCode
        fields = ["id", "code", "discount_percent", "is_active", "max_uses", "times_used", "created_at"]
