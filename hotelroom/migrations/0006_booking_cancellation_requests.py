from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hotelroom", "0014_unique_room_rating_per_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="cancel_request_status",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("requested", "Requested"),
                    ("rejected", "Rejected"),
                    ("approved", "Approved"),
                ],
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancel_request_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancel_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancel_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="cancel_reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_cancellation_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
