from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hotelroom", "0014_unique_room_rating_per_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="sent_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
