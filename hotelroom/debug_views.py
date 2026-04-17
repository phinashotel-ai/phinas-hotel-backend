from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from datetime import date
from .models import Room, Booking


class DebugRoomAvailabilityView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        try:
            room = Room.objects.get(pk=pk)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=404)
        
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')
        
        if not check_in_str or not check_out_str:
            return Response({"error": "check_in and check_out parameters required"}, status=400)
        
        try:
            check_in = date.fromisoformat(check_in_str)
            check_out = date.fromisoformat(check_out_str)
        except ValueError:
            return Response({"error": "Invalid date format"}, status=400)
        
        # Get all bookings for this room
        all_bookings = Booking.objects.filter(room=room).values(
            'id', 'check_in', 'check_out', 'status', 'user__username'
        )
        
        # Get active bookings
        active_bookings = Booking.objects.filter(
            room=room, 
            status__in=("confirmed", "checked_in")
        ).values('id', 'check_in', 'check_out', 'status', 'user__username')
        
        # Check for overlapping bookings
        overlapping = Booking.objects.filter(
            room=room,
            status__in=("confirmed", "checked_in"),
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
        
        overlapping_data = overlapping.values('id', 'check_in', 'check_out', 'status', 'user__username')
        
        return Response({
            "room_id": room.id,
            "room_name": room.name,
            "room_status": room.status,
            "max_bookings": room.get_booking_limit(),
            "requested_dates": {
                "check_in": check_in_str,
                "check_out": check_out_str
            },
            "all_bookings": list(all_bookings),
            "active_bookings": list(active_bookings),
            "overlapping_bookings": list(overlapping_data),
            "overlap_count": overlapping.count(),
            "is_available": overlapping.count() < room.get_booking_limit()
        })
