# Example: How room extension affects availability

# Current extension logic (from views.py):
def _extend_stay(self, request, booking):
    # Only checked-in bookings can be extended
    if booking.status != "checked_in":
        return Response({"error": "Only checked-in bookings can be extended."})
    
    extend_days = int(request.data.get("extend_days", 1))
    new_check_out = booking.check_out + timedelta(days=extend_days)
    
    # Check room availability for extended period
    overlapping = Booking.objects.filter(
        room=booking.room,
        status__in=("confirmed", "checked_in"),
        check_in__lt=new_check_out,  # New extended checkout
        check_out__gt=booking.check_out,  # Original checkout
    ).exclude(pk=booking.pk).count()
    
    if overlapping >= booking.room.get_booking_limit():
        return Response({"error": "Room not available for extra nights."})
    
    # Update booking with new checkout date
    booking.check_out = new_check_out
    booking.save()  # This triggers recalculation and room status sync

# Room availability check (from views.py):
def room_availability_check():
    # When searching rooms, the system excludes unavailable rooms
    for room in rooms:
        overlap = Booking.objects.filter(
            room=room,
            status__in=("confirmed", "checked_in"),
            check_in__lt=checkout_date,  # Includes extended checkouts
            check_out__gt=checkin_date,
        ).count()
        
        if overlap >= room.get_booking_limit():
            # Room is unavailable - won't show in search results
            unavailable_ids.append(room.id)
