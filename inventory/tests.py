from decimal import Decimal
from django.test import TestCase
from .models import InventoryItem, StockMovement


class InventoryItemTests(TestCase):
    def setUp(self):
        self.rice = InventoryItem.objects.create(
            name='Rice', unit='g', quantity_in_stock=1000, reorder_level=200, cost_per_unit=Decimal('0.01')
        )

    def test_is_low_stock(self):
        self.assertFalse(self.rice.is_low_stock)
        self.rice.quantity_in_stock = 200
        self.rice.save()
        self.assertTrue(self.rice.is_low_stock)

    def test_adjust_stock_out_reduces_quantity_and_logs_movement(self):
        self.rice.adjust_stock(quantity=300, movement_type=StockMovement.MovementType.OUT, reason='test sale')
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantity_in_stock, Decimal('700'))
        movement = self.rice.movements.latest('created_at')
        self.assertEqual(movement.movement_type, StockMovement.MovementType.OUT)
        self.assertEqual(movement.quantity, Decimal('300'))

    def test_adjust_stock_in_increases_quantity(self):
        self.rice.adjust_stock(quantity=500, movement_type=StockMovement.MovementType.IN, reason='restock')
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantity_in_stock, Decimal('1500'))

    def test_adjust_stock_out_raises_when_insufficient(self):
        with self.assertRaises(ValueError):
            self.rice.adjust_stock(quantity=5000, movement_type=StockMovement.MovementType.OUT)
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantity_in_stock, Decimal('1000'))  # unchanged


class InventoryApiTests(TestCase):
    def setUp(self):
        self.item = InventoryItem.objects.create(
            name='Cheese', unit='g', quantity_in_stock=100, reorder_level=150, cost_per_unit=Decimal('0.05')
        )

    def test_low_stock_endpoint_returns_item_below_reorder_level(self):
        resp = self.client.get('/api/inventory/items/low-stock/')
        self.assertEqual(resp.status_code, 200)
        names = [row['name'] for row in resp.json()]
        self.assertIn('Cheese', names)

    def test_adjust_stock_endpoint(self):
        resp = self.client.post(
            f'/api/inventory/items/{self.item.id}/adjust-stock/',
            data={'quantity': '50', 'movement_type': 'IN', 'reason': 'delivery'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.json()['quantity_in_stock']), Decimal('150'))

    def test_adjust_stock_endpoint_rejects_insufficient_out(self):
        resp = self.client.post(
            f'/api/inventory/items/{self.item.id}/adjust-stock/',
            data={'quantity': '9999', 'movement_type': 'OUT'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
