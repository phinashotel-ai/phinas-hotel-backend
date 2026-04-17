from django.core.management.base import BaseCommand
from hotelroom.models import Room


class Command(BaseCommand):
    help = 'Fix room booking limits to ensure they are set to 1 for proper availability checking'

    def handle(self, *args, **options):
        # Update all rooms to have max_bookings = 1 if they don't have it set properly
        rooms_updated = Room.objects.filter(max_bookings__gt=1).update(max_bookings=1)
        rooms_with_zero = Room.objects.filter(max_bookings=0).update(max_bookings=1)
        
        total_updated = rooms_updated + rooms_with_zero
        
        if total_updated > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {total_updated} rooms to have max_bookings=1')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All rooms already have correct booking limits')
            )
        
        # Sync all room statuses
        for room in Room.objects.all():
            room.sync_status()
        
        self.stdout.write(
            self.style.SUCCESS('Room statuses synchronized')
        )