from django.contrib import admin
from .models import Room, Booking


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["room_number", "name", "room_type", "price_per_night", "capacity", "max_bookings", "status", "floor"]
    list_filter  = ["room_type", "status", "floor"]
    search_fields = ["room_number", "name"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ["id", "user", "room", "check_in", "check_out", "guests", "meal_category", "total_price", "status", "created_at"]
    list_filter   = ["status", "meal_category", "check_in", "check_out"]
    search_fields = ["user__username", "user__email", "room__name", "room__room_number"]
    readonly_fields = ["total_price", "created_at"]
    list_select_related = ("user", "room")
    show_full_result_count = False
    list_per_page = 25
