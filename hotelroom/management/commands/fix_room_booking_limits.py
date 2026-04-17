from django.core.management.base import BaseCommand
from hotelroom.models import Room


class Command(BaseCommand):
    help = 'Fix room booking limits and sync room statuses'

    def handle(self, *args, **options):
        # Only update rooms that have max_bookings = 0 or None
        rooms_with_zero = Room.objects.filter(max_bookings__isnull=True).update(max_bookings=1)
        rooms_with_zero += Room.objects.filter(max_bookings=0).update(max_bookings=1)
        
        if rooms_with_zero > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Updated {rooms_with_zero} rooms with missing booking limits')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All rooms have valid booking limits')
            )
        
        # Show current room booking limits
        rooms = Room.objects.all().values('id', 'name', 'room_number', 'max_bookings', 'capacity')
        self.stdout.write('\nCurrent room booking limits:')
        for room in rooms:
            self.stdout.write(
                f"Room {room['room_number']} ({room['name']}): max_bookings={room['max_bookings']}, capacity={room['capacity']}"
            )
        
        # Sync all room statuses
        for room in Room.objects.all():
            room.sync_status()
        
        self.stdout.write(
            self.style.SUCCESS('\nRoom statuses synchronized')
        )