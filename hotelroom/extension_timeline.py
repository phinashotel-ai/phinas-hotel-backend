# Timeline: When Users Can Extend Their Stay

"""
BOOKING LIFECYCLE & EXTENSION AVAILABILITY:

1. BOOKING CREATED (status: "pending")
   ❌ Extension: NOT ALLOWED
   - User must wait for confirmation

2. BOOKING CONFIRMED (status: "confirmed") 
   ❌ Extension: NOT ALLOWED
   - User must check in first

3. CHECK-IN TIME ARRIVES
   ✅ User can check in (changes status to "checked_in")

4. CHECKED IN (status: "checked_in")
   ✅ Extension: ALLOWED
   - This is the ONLY status that allows extensions
   - Can extend 1-7 days at a time
   - Must be before original checkout time

5. CHECKOUT TIME PASSES
   ❌ Extension: NOT ALLOWED
   - System message: "This stay has already passed the checkout date"
   - Status may auto-change to "completed"

6. CHECKED OUT (status: "checked_out")
   ❌ Extension: NOT ALLOWED
   - Stay is officially ended

Example Timeline:
- Jan 1: Book room (pending) ❌ No extension
- Jan 5: Confirmed ❌ No extension  
- Jan 10 2PM: Check in ✅ CAN EXTEND
- Jan 12 10AM: Still checked in ✅ CAN EXTEND
- Jan 15 12PM: Original checkout time ❌ No extension after this
"""

# Code implementation from views.py:
def _extend_stay(self, request, booking):
    # Check 1: Must be checked in
    if booking.status != "checked_in":
        return Response({
            "error": "Only checked-in bookings can be extended."
        }, status=400)
    
    # Check 2: Must be before checkout time
    if timezone.now() > _booking_check_out_dt(booking):
        return Response({
            "error": "This stay has already passed the checkout date."
        }, status=400)
    
    # Check 3: Extension days validation
    extend_days = int(request.data.get("extend_days", 1))
    if extend_days < 1 or extend_days > 7:
        return Response({
            "error": "You can extend between 1 and 7 days at a time."
        }, status=400)
    
    # Check 4: Room availability for extended period
    new_check_out = booking.check_out + timedelta(days=extend_days)
    overlapping = Booking.objects.filter(
        room=booking.room,
        status__in=("pending", "confirmed", "checked_in"),
        check_in__lt=new_check_out,
        check_out__gt=booking.check_out,
    ).exclude(pk=booking.pk).count()
    
    if overlapping >= booking.room.get_booking_limit():
        return Response({
            "error": "This room is not available for the extra nights."
        }, status=400)
    
    # All checks passed - allow extension
    booking.check_out = new_check_out
    booking.save()  # Recalculates pricing automatically
    
    return Response({
        "message": "Booking extended successfully.",
        "booking": BookingSerializer(booking).data
    })