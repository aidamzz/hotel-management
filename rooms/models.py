from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Room(models.Model):
    class View(models.TextChoices):
        SEA = "sea", "Sea"
        MOUNTAIN = "mountain", "Mountain"
        YARD = "yard", "Yard"

    label = models.CharField(max_length=64, unique=True)
    beds = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    view = models.CharField(max_length=16, choices=View.choices)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.label


class Booking(models.Model):
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    user_identifier = models.CharField(max_length=255)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="booking_check_out_after_check_in",
            )
        ]
        indexes = [
            models.Index(fields=["room", "check_in", "check_out"]),
        ]

    def __str__(self):
        return f"{self.user_identifier} @ {self.room}"
