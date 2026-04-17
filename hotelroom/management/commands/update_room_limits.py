from django.core.management.base import BaseCommand
from hotelroom.models import Room


class Command(BaseCommand):
    help = 'Update specific room booking limits based on room type or capacity'

    def add_arguments(self, parser):
        parser.add_argument('--room-id', type=int, help='Specific room ID to update')
        parser.add_argument('--max-bookings', type=int, help='New max_bookings value')
        parser.add_argument('--auto-update', action='store_true', help='Auto-update based on room capacity')

    def handle(self, *args, **options):
        if options['room_id'] and options['max_bookings']:
            # Update specific room
            try:
                room = Room.objects.get(id=options['room_id'])
                old_limit = room.max_bookings
                room.max_bookings = options['max_bookings']
                room.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated Room {room.room_number} ({room.name}): '
                        f'max_bookings changed from {old_limit} to {room.max_bookings}'
                    )
                )
            except Room.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Room with ID {options["room_id"]} not found'))
        
        elif options['auto_update']:
            # Auto-update based on room capacity/type
            updated_rooms = []
            
            # Family rooms or large capacity rooms might allow multiple bookings
            large_rooms = Room.objects.filter(capacity__gte=5)
            for room in large_rooms:
                if room.room_type == 'family' or room.capacity >= 8:
                    # Large family rooms can have multiple bookings
                    new_limit = min(3, room.capacity // 2)  # Max 3 bookings, or capacity/2
                    if room.max_bookings != new_limit:
                        old_limit = room.max_bookings
                        room.max_bookings = new_limit
                        room.save()
                        updated_rooms.append(f'Room {room.room_number}: {old_limit} -> {new_limit}')
            
            if updated_rooms:
                self.stdout.write(self.style.SUCCESS('Updated rooms:'))
                for update in updated_rooms:
                    self.stdout.write(f'  {update}')
            else:
                self.stdout.write(self.style.SUCCESS('No rooms needed updating'))
        
        else:
            # Show current configuration
            self.stdout.write('Current room configuration:')
            rooms = Room.objects.all().order_by('room_number')
            for room in rooms:
                self.stdout.write(
                    f'Room {room.room_number} ({room.room_type}): '
                    f'capacity={room.capacity}, max_bookings={room.max_bookings}'
                )