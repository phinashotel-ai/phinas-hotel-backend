from django.core.management.base import BaseCommand
from hotelroom.models import Room


class Command(BaseCommand):
    help = "Seed sample hotel rooms"

    def handle(self, *args, **kwargs):
        Room.objects.all().delete()

        rooms = [
            {
                "name": "Standard Room",
                "room_number": "101",
                "room_type": "standard",
                "price_per_night": 2500,
                "capacity": 2,
                "floor": 1,
                "description": "A comfortable standard room with all essential amenities for a pleasant stay.",
                "amenities": ["Free WiFi", "Air Conditioning", "TV", "Hot Shower", "Mini Fridge"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Standard Room",
                "room_number": "102",
                "room_type": "standard",
                "price_per_night": 2500,
                "capacity": 2,
                "floor": 1,
                "description": "A comfortable standard room with all essential amenities for a pleasant stay.",
                "amenities": ["Free WiFi", "Air Conditioning", "TV", "Hot Shower", "Mini Fridge"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Deluxe Room",
                "room_number": "201",
                "room_type": "deluxe",
                "price_per_night": 4500,
                "capacity": 2,
                "floor": 2,
                "description": "Spacious deluxe room with premium furnishings and a stunning city view.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Bathtub", "Mini Bar", "City View"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Deluxe Room",
                "room_number": "202",
                "room_type": "deluxe",
                "price_per_night": 4500,
                "capacity": 2,
                "floor": 2,
                "description": "Spacious deluxe room with premium furnishings and a stunning city view.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Bathtub", "Mini Bar", "City View"],
                "image_url": "",
                "status": "occupied",
            },
            {
                "name": "Family Room",
                "room_number": "301",
                "room_type": "family",
                "price_per_night": 7500,
                "capacity": 4,
                "floor": 3,
                "description": "Ideal for families, featuring two queen beds, a kitchenette, and a private balcony.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Kitchenette", "Balcony", "2 Queen Beds"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Family Room",
                "room_number": "302",
                "room_type": "family",
                "price_per_night": 7500,
                "capacity": 4,
                "floor": 3,
                "description": "Ideal for families, featuring two queen beds, a kitchenette, and a private balcony.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Kitchenette", "Balcony", "2 Queen Beds"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Executive Suite",
                "room_number": "401",
                "room_type": "suite",
                "price_per_night": 12000,
                "capacity": 2,
                "floor": 4,
                "description": "Our premier suite with a separate living area, king bed, and panoramic views.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Jacuzzi", "Mini Bar", "Living Area", "Panoramic View", "Breakfast Included"],
                "image_url": "",
                "status": "available",
            },
            {
                "name": "Presidential Suite",
                "room_number": "402",
                "room_type": "suite",
                "price_per_night": 18000,
                "capacity": 3,
                "floor": 4,
                "description": "The pinnacle of luxury — a full suite with butler service and exclusive amenities.",
                "amenities": ["Free WiFi", "Air Conditioning", "Smart TV", "Jacuzzi", "Full Bar", "Living Area", "Dining Area", "Butler Service", "Breakfast Included"],
                "image_url": "",
                "status": "available",
            },
        ]

        for r in rooms:
            Room.objects.create(**r)
            self.stdout.write(f"  Created room {r['room_number']} - {r['name']}")

        self.stdout.write(self.style.SUCCESS(f"\nSeeded {len(rooms)} rooms successfully."))
