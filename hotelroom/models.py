from django.db import models
from user.models import CustomUser
from decimal import Decimal
import uuid


class Room(models.Model):
    ROOM_TYPES = [
        ("standard", "Standard"),
        ("deluxe", "Deluxe"),
        ("suite", "Suite"),
        ("family", "Family"),
    ]
    STATUS_CHOICES = [
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("maintenance", "Maintenance"),
    ]

    name            = models.CharField(max_length=100)
    room_number     = models.CharField(max_length=10, unique=True)
    room_type       = models.CharField(max_length=20, choices=ROOM_TYPES, default="standard")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity        = models.PositiveIntegerField(default=2)
    max_bookings    = models.PositiveIntegerField(
        default=1,
        help_text="Max simultaneous bookings allowed for this room (usually 1)."
    )
    description     = models.TextField(blank=True)
    amenities       = models.JSONField(default=list, blank=True)
    image_url       = models.URLField(blank=True)
    room_image      = models.FileField(upload_to="room-images/", blank=True, null=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    floor           = models.PositiveIntegerField(default=1)
    free_food_guest_limit = models.PositiveIntegerField(default=2)
    extra_guest_fee_per_night = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    lunch_price_per_guest = models.DecimalField(max_digits=10, decimal_places=2, default=250)
    dinner_price_per_guest = models.DecimalField(max_digits=10, decimal_places=2, default=400)
    extra_guest_lunch_price_per_guest = models.DecimalField(max_digits=10, decimal_places=2, default=250)
    extra_guest_dinner_price_per_guest = models.DecimalField(max_digits=10, decimal_places=2, default=400)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["room_number"]

    def __str__(self):
        return f"{self.room_number} - {self.name}"

    def get_booking_limit(self):
        return max(1, self.capacity or self.max_bookings or 1)

    def sync_status(self):
        if self.status == "maintenance":
            return
        from datetime import date
        today = date.today()
        active_today = self.bookings.filter(
            status__in=("pending", "confirmed", "checked_in"),
            check_in__lte=today,
            check_out__gt=today,
        ).count()
        new_status = "occupied" if active_today >= self.get_booking_limit() else "available"
        if self.status != new_status:
            Room.objects.filter(pk=self.pk).update(status=new_status)
            self.status = new_status

    def get_meal_rate(self, meal_category, extra_guest=False):
        if meal_category == "lunch":
            return self.extra_guest_lunch_price_per_guest if extra_guest else self.lunch_price_per_guest
        if meal_category == "dinner":
            return self.extra_guest_dinner_price_per_guest if extra_guest else self.dinner_price_per_guest
        if meal_category == "both":
            lunch_rate = self.extra_guest_lunch_price_per_guest if extra_guest else self.lunch_price_per_guest
            dinner_rate = self.extra_guest_dinner_price_per_guest if extra_guest else self.dinner_price_per_guest
            return lunch_rate + dinner_rate
        return Decimal("0")


class PromoCode(models.Model):
    code             = models.CharField(max_length=30, unique=True)
    discount_percent = models.PositiveIntegerField(default=20, help_text="Discount percentage e.g. 20 = 20%")
    is_active        = models.BooleanField(default=True)
    max_uses         = models.PositiveIntegerField(default=100)
    times_used       = models.PositiveIntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("confirmed", "Confirmed"),
        ("checked_in", "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    CANCELLATION_REQUEST_STATUS_CHOICES = [
        ("none", "None"),
        ("requested", "Requested"),
        ("rejected", "Rejected"),
        ("approved", "Approved"),
    ]
    MEAL_CATEGORY_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("both", "Both"),
    ]
    user             = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="bookings")
    room             = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    check_in         = models.DateField()
    check_out        = models.DateField()
    guests           = models.PositiveIntegerField(default=1)
    meal_category    = models.CharField(max_length=20, choices=MEAL_CATEGORY_CHOICES, default="breakfast")
    meal_addon_rate  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    meal_addon_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price      = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    cancel_request_status = models.CharField(
        max_length=20,
        choices=CANCELLATION_REQUEST_STATUS_CHOICES,
        default="none",
    )
    cancel_request_reason = models.TextField(blank=True)
    cancel_requested_at = models.DateTimeField(blank=True, null=True)
    cancel_reviewed_at = models.DateTimeField(blank=True, null=True)
    cancel_reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="reviewed_cancellation_requests",
        blank=True,
        null=True,
    )
    special_requests = models.TextField(blank=True)
    promo_code       = models.CharField(max_length=30, blank=True)
    discount_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_food_guests = models.PositiveIntegerField(default=2)
    extra_guest_count = models.PositiveIntegerField(default=0)
    extra_guest_fee_per_night = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    extra_guest_fee_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference_number = models.CharField(max_length=30, blank=True, null=True, unique=True, editable=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def _generate_reference_number():
        return f"PH-{uuid.uuid4().hex[:10].upper()}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self._generate_reference_number()
        if self.check_in and self.check_out and self.room:
            nights = (self.check_out - self.check_in).days
            base = nights * self.room.price_per_night
            free_limit = self.room.free_food_guest_limit or 0
            extra_fee = self.room.extra_guest_fee_per_night or Decimal("0")
            regular_meal_rate = self.room.get_meal_rate(self.meal_category, extra_guest=False)
            extra_meal_rate = self.room.get_meal_rate(self.meal_category, extra_guest=True)
            self.free_food_guests = min(self.guests or 0, free_limit)
            self.extra_guest_count = max((self.guests or 0) - free_limit, 0)
            self.extra_guest_fee_per_night = extra_fee
            self.extra_guest_fee_total = Decimal(str(self.extra_guest_count)) * extra_fee * nights
            self.meal_addon_rate = regular_meal_rate
            self.meal_addon_total = (
                Decimal(str(self.free_food_guests)) * regular_meal_rate * nights
                + Decimal(str(self.extra_guest_count)) * extra_meal_rate * nights
            )
            self.total_price = base + self.extra_guest_fee_total + self.meal_addon_total - Decimal(str(self.discount_amount))
        super().save(*args, **kwargs)
        self.room.sync_status()

    def delete(self, *args, **kwargs):
        room = self.room
        super().delete(*args, **kwargs)
        room.sync_status()

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} - {self.room.name}"


class Payment(models.Model):
    METHOD_CHOICES = [
        ("gcash", "GCash"),
        ("cash",  "Cash on Arrival"),
        ("card",  "Credit/Debit Card"),
    ]
    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("paid",     "Paid"),
        ("failed",   "Failed"),
        ("refunded", "Refunded"),
    ]
    booking          = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")
    method           = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    amount           = models.DecimalField(max_digits=10, decimal_places=2)
    sent_amount      = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment #{self.id} - Booking #{self.booking_id} - {self.status}"


class RoomRating(models.Model):
    user    = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="ratings")
    room    = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="ratings")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="rating", null=True, blank=True)
    stars   = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "room"], name="unique_room_rating_per_user"),
        ]

    def __str__(self):
        return f"{self.user.username} rated {self.room.name}: {self.stars}★"
