from django.db import migrations, models


def delete_regular_rooms(apps, schema_editor):
    Room = apps.get_model("hotelroom", "Room")
    Room.objects.filter(room_type="regular").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hotelroom", "0016_merge_0007_alter_booking_status_0015_payment_sent_amount"),
    ]

    operations = [
        migrations.RunPython(delete_regular_rooms, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="room",
            name="room_type",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("deluxe", "Deluxe"),
                    ("suite", "Suite"),
                    ("family", "Family"),
                ],
                default="standard",
                max_length=20,
            ),
        ),
    ]
