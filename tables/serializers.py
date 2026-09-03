from rest_framework import serializers
from .models import DiningTable, Reservation


class DiningTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiningTable
        fields = ['id', 'number', 'capacity', 'status']


class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='table.number', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'table', 'table_number', 'customer_name', 'customer_phone',
            'party_size', 'reservation_time', 'duration_minutes', 'status',
            'notes', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate(self, attrs):
        table = attrs.get('table') or getattr(self.instance, 'table', None)
        party_size = attrs.get('party_size') or getattr(self.instance, 'party_size', None)
        reservation_time = attrs.get('reservation_time') or getattr(self.instance, 'reservation_time', None)
        duration = attrs.get('duration_minutes') or getattr(self.instance, 'duration_minutes', 90)

        if table and party_size and party_size > table.capacity:
            raise serializers.ValidationError(
                f"Table {table.number} seats {table.capacity}, party of {party_size} won't fit."
            )

        if table and reservation_time:
            from datetime import timedelta
            new_start = reservation_time
            new_end = reservation_time + timedelta(minutes=duration)
            clashes = Reservation.objects.filter(table=table).exclude(
                status__in=[Reservation.Status.CANCELLED, Reservation.Status.COMPLETED]
            )
            if self.instance:
                clashes = clashes.exclude(pk=self.instance.pk)
            for other in clashes:
                if new_start < other.end_time and other.reservation_time < new_end:
                    raise serializers.ValidationError(
                        f"Table {table.number} is already booked for "
                        f"{other.customer_name} at that time."
                    )
        return attrs
