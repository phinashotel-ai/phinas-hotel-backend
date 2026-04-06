from django.db import migrations, models


def dedupe_room_ratings(apps, schema_editor):
    RoomRating = apps.get_model("hotelroom", "RoomRating")

    pairs = (
        RoomRating.objects.values("user_id", "room_id")
        .annotate(count=models.Count("id"))
        .filter(count__gt=1)
    )

    for pair in pairs:
        duplicates = list(
            RoomRating.objects.filter(
                user_id=pair["user_id"],
                room_id=pair["room_id"],
            ).order_by("-created_at", "-id")
        )
        for rating in duplicates[1:]:
            rating.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("hotelroom", "0005_booking_reference_number"),
    ]

    operations = [
        migrations.RunPython(dedupe_room_ratings, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="roomrating",
            constraint=models.UniqueConstraint(
                fields=["user", "room"],
                name="unique_room_rating_per_user",
            ),
        ),
    ]
