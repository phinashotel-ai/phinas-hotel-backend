from datetime import time

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hotelroom", "0017_remove_regular_room_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="check_in_time",
            field=models.TimeField(default=time(14, 0)),
        ),
        migrations.AddField(
            model_name="booking",
            name="check_out_time",
            field=models.TimeField(default=time(12, 0)),
        ),
    ]
