from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from .models import DiningTable, Reservation
from .serializers import ReservationSerializer


class DiningTableApiTests(TestCase):
    def setUp(self):
        self.small = DiningTable.objects.create(number=1, capacity=2)
        self.large = DiningTable.objects.create(number=2, capacity=6)
        DiningTable.objects.create(number=3, capacity=4, status=DiningTable.Status.OCCUPIED)

    def test_available_endpoint_excludes_occupied(self):
        resp = self.client.get('/api/tables/available/')
        numbers = [row['number'] for row in resp.json()]
        self.assertIn(1, numbers)
        self.assertIn(2, numbers)
        self.assertNotIn(3, numbers)

    def test_available_endpoint_filters_by_party_size(self):
        resp = self.client.get('/api/tables/available/?party_size=4')
        numbers = [row['number'] for row in resp.json()]
        self.assertEqual(numbers, [2])  # only the 6-seat table fits a party of 4


class ReservationValidationTests(TestCase):
    def setUp(self):
        self.table = DiningTable.objects.create(number=5, capacity=4)
        self.start = timezone.now() + timedelta(hours=2)

    def test_rejects_party_larger_than_capacity(self):
        serializer = ReservationSerializer(data={
            'table': self.table.id, 'customer_name': 'Big Group', 'party_size': 10,
            'reservation_time': self.start, 'duration_minutes': 60,
        })
        self.assertFalse(serializer.is_valid())

    def test_rejects_overlapping_reservation_on_same_table(self):
        Reservation.objects.create(
            table=self.table, customer_name='First', party_size=2,
            reservation_time=self.start, duration_minutes=90,
        )
        overlapping_time = self.start + timedelta(minutes=30)
        serializer = ReservationSerializer(data={
            'table': self.table.id, 'customer_name': 'Second', 'party_size': 2,
            'reservation_time': overlapping_time, 'duration_minutes': 60,
        })
        self.assertFalse(serializer.is_valid())

    def test_allows_non_overlapping_reservation(self):
        Reservation.objects.create(
            table=self.table, customer_name='First', party_size=2,
            reservation_time=self.start, duration_minutes=60,
        )
        later_time = self.start + timedelta(hours=2)
        serializer = ReservationSerializer(data={
            'table': self.table.id, 'customer_name': 'Second', 'party_size': 2,
            'reservation_time': later_time, 'duration_minutes': 60,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ReservationApiTests(TestCase):
    def setUp(self):
        self.table = DiningTable.objects.create(number=7, capacity=4)
        self.start = timezone.now() + timedelta(hours=1)

    def test_creating_reservation_marks_table_reserved(self):
        resp = self.client.post('/api/reservations/', data={
            'table': self.table.id, 'customer_name': 'Dana', 'party_size': 3,
            'reservation_time': self.start.isoformat(), 'duration_minutes': 90,
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, DiningTable.Status.RESERVED)

    def test_seat_then_complete_lifecycle(self):
        resp = self.client.post('/api/reservations/', data={
            'table': self.table.id, 'customer_name': 'Eli', 'party_size': 2,
            'reservation_time': self.start.isoformat(), 'duration_minutes': 60,
        }, content_type='application/json')
        reservation_id = resp.json()['id']

        seat_resp = self.client.post(f'/api/reservations/{reservation_id}/seat/')
        self.assertEqual(seat_resp.status_code, 200)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, DiningTable.Status.OCCUPIED)

        complete_resp = self.client.post(f'/api/reservations/{reservation_id}/complete/')
        self.assertEqual(complete_resp.status_code, 200)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, DiningTable.Status.AVAILABLE)
