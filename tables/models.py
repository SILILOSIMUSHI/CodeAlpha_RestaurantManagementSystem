from django.db import models
from django.core.validators import MinValueValidator


class DiningTable(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        RESERVED = 'RESERVED', 'Reserved'
        MAINTENANCE = 'MAINTENANCE', 'Under maintenance'

    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Table {self.number} (seats {self.capacity})"


class Reservation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        SEATED = 'SEATED', 'Seated'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    table = models.ForeignKey(DiningTable, on_delete=models.CASCADE, related_name='reservations')
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=30, blank=True)
    party_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reservation_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['reservation_time']

    def __str__(self):
        return f"{self.customer_name} @ Table {self.table.number} on {self.reservation_time:%Y-%m-%d %H:%M}"

    @property
    def end_time(self):
        from datetime import timedelta
        return self.reservation_time + timedelta(minutes=self.duration_minutes)
