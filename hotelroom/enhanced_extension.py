# Enhanced extension system supporting both hours and days

from datetime import timedelta
from decimal import Decimal

def _extend_stay_enhanced(self, request, booking):
    """Enhanced extension supporting both hourly and daily extensions"""
    
    if booking.status != "checked_in":
        return Response({"error": "Only checked-in bookings can be extended."})
    
    # Get extension parameters
    extend_days = int(request.data.get("extend_days", 0))
    extend_hours = int(request.data.get("extend_hours", 0))
    
    if extend_days == 0 and extend_hours == 0:
        return Response({"error": "Please specify extension days or hours."})
    
    # Validate limits
    if extend_days > 7:
        return Response({"error": "Maximum 7 days extension at a time."})
    if extend_hours > 24:
        return Response({"error": "Maximum 24 hours extension at a time."})
    
    # Calculate new checkout datetime
    extension_delta = timedelta(days=extend_days, hours=extend_hours)
    current_checkout_dt = datetime.combine(booking.check_out, booking.check_out_time)
    new_checkout_dt = current_checkout_dt + extension_delta
    new_check_out_date = new_checkout_dt.date()
    new_check_out_time = new_checkout_dt.time()
    
    # Check availability for extended period
    overlapping = Booking.objects.filter(
        room=booking.room,
        status__in=("pending", "confirmed", "checked_in"),
        check_in__lt=new_check_out_date,
        check_out__gt=booking.check_out,
    ).exclude(pk=booking.pk).count()
    
    if overlapping >= booking.room.get_booking_limit():
        return Response({"error": "Room not available for the extended period."})
    
    # Calculate additional charges
    hourly_rate = booking.room.price_per_night / 24  # Hourly rate
    additional_charge = Decimal('0')
    
    if extend_hours > 0:
        additional_charge += hourly_rate * extend_hours
    if extend_days > 0:
        additional_charge += booking.room.price_per_night * extend_days
    
    # Update booking
    booking.check_out = new_check_out_date
    booking.check_out_time = new_check_out_time
    booking.total_price += additional_charge
    booking.save()
    
    return Response({
        "message": f"Stay extended by {extend_days} days and {extend_hours} hours",
        "additional_charge": additional_charge,
        "new_checkout": f"{new_check_out_date} at {new_check_out_time}",
        "booking": BookingSerializer(booking).data
    })

# API endpoint usage examples:
# POST /api/bookings/{id}/
# {
#     "action": "extend_stay",
#     "extend_days": 2,
#     "extend_hours": 4
# }