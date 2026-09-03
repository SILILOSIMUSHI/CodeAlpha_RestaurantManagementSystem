import json
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from menu.models import Category, MenuItem, MenuItemIngredient
from inventory.models import InventoryItem
from tables.models import DiningTable
from .models import Order
from . import services


class OrderServiceTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Mains', display_order=1)
        self.chicken = InventoryItem.objects.create(name='Chicken', unit='g', quantity_in_stock=1000, reorder_level=100)
        self.rice = InventoryItem.objects.create(name='Rice', unit='g', quantity_in_stock=2000, reorder_level=200)
        self.dish = MenuItem.objects.create(category=category, name='Chicken Bowl', price=Decimal('10.00'))
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.chicken, quantity_required=200)
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.rice, quantity_required=150)
        self.table = DiningTable.objects.create(number=1, capacity=4)

    def test_place_order_deducts_stock_and_occupies_table(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Alice', items_data=[{'menu_item': self.dish, 'quantity': 2}],
        )
        self.chicken.refresh_from_db()
        self.rice.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('600'))
        self.assertEqual(self.rice.quantity_in_stock, Decimal('1700'))
        self.assertEqual(self.table.status, DiningTable.Status.OCCUPIED)
        self.assertEqual(order.total_amount, Decimal('20.00'))

    def test_place_order_rejects_occupied_table(self):
        self.table.status = DiningTable.Status.OCCUPIED
        self.table.save()
        with self.assertRaises(ValidationError):
            services.place_order(
                table=self.table, order_type=Order.OrderType.DINE_IN,
                customer_name='Bob', items_data=[{'menu_item': self.dish, 'quantity': 1}],
            )

    def test_place_order_rejects_insufficient_stock_and_does_not_deduct_anything(self):
        with self.assertRaises(ValidationError):
            services.place_order(
                table=self.table, order_type=Order.OrderType.DINE_IN,
                customer_name='Carl', items_data=[{'menu_item': self.dish, 'quantity': 100}],
            )
        self.chicken.refresh_from_db()
        self.rice.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('1000'))  # untouched
        self.assertEqual(self.rice.quantity_in_stock, Decimal('2000'))     # untouched

    def test_place_order_rejects_unavailable_item(self):
        self.dish.is_available = False
        self.dish.save()
        with self.assertRaises(ValidationError):
            services.place_order(
                table=self.table, order_type=Order.OrderType.DINE_IN,
                customer_name='Dana', items_data=[{'menu_item': self.dish, 'quantity': 1}],
            )

    def test_takeaway_order_does_not_require_or_touch_table(self):
        order = services.place_order(
            table=None, order_type=Order.OrderType.TAKEAWAY,
            customer_name='Eli', items_data=[{'menu_item': self.dish, 'quantity': 1}],
        )
        self.assertIsNone(order.table)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, DiningTable.Status.AVAILABLE)

    def test_complete_order_frees_table(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Finn', items_data=[{'menu_item': self.dish, 'quantity': 1}],
        )
        services.complete_order(order)
        order.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(self.table.status, DiningTable.Status.AVAILABLE)

    def test_cancel_order_restocks_inventory_and_frees_table(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Gia', items_data=[{'menu_item': self.dish, 'quantity': 2}],
        )
        services.cancel_order(order)
        self.chicken.refresh_from_db()
        self.rice.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('1000'))  # restocked
        self.assertEqual(self.rice.quantity_in_stock, Decimal('2000'))     # restocked
        self.assertEqual(self.table.status, DiningTable.Status.AVAILABLE)

    def test_add_item_to_order_deducts_additional_stock(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Huan', items_data=[{'menu_item': self.dish, 'quantity': 1}],
        )
        services.add_item_to_order(order=order, menu_item=self.dish, quantity=1)
        self.chicken.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('600'))  # 1000 - 200 - 200
        self.assertEqual(order.items.count(), 2)

    def test_cannot_add_item_to_completed_order(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Ivy', items_data=[{'menu_item': self.dish, 'quantity': 1}],
        )
        services.complete_order(order)
        with self.assertRaises(ValidationError):
            services.add_item_to_order(order=order, menu_item=self.dish, quantity=1)


class OrderApiTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Mains', display_order=1)
        self.chicken = InventoryItem.objects.create(name='Chicken', unit='g', quantity_in_stock=1000, reorder_level=100)
        self.dish = MenuItem.objects.create(category=category, name='Chicken Bowl', price=Decimal('10.00'))
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.chicken, quantity_required=200)
        self.table = DiningTable.objects.create(number=1, capacity=4)

    def test_create_order_via_api(self):
        resp = self.client.post('/api/orders/', data=json.dumps({
            'table': self.table.id, 'order_type': 'DINE_IN', 'customer_name': 'Jo',
            'items': [{'menu_item': self.dish.id, 'quantity': 2}],
        }), content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body['status'], 'PENDING')
        self.assertEqual(Decimal(body['total_amount']), Decimal('20.00'))

    def test_dine_in_order_without_table_is_rejected(self):
        resp = self.client.post('/api/orders/', data=json.dumps({
            'order_type': 'DINE_IN', 'items': [{'menu_item': self.dish.id, 'quantity': 1}],
        }), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_set_status_enforces_valid_transitions(self):
        create_resp = self.client.post('/api/orders/', data=json.dumps({
            'table': self.table.id, 'order_type': 'DINE_IN',
            'items': [{'menu_item': self.dish.id, 'quantity': 1}],
        }), content_type='application/json')
        order_id = create_resp.json()['id']

        # PENDING -> READY is not a valid direct jump
        bad_resp = self.client.post(f'/api/orders/{order_id}/set-status/', data=json.dumps({'status': 'READY'}), content_type='application/json')
        self.assertEqual(bad_resp.status_code, 400)

        # PENDING -> PREPARING is valid
        good_resp = self.client.post(f'/api/orders/{order_id}/set-status/', data=json.dumps({'status': 'PREPARING'}), content_type='application/json')
        self.assertEqual(good_resp.status_code, 200)
        self.assertEqual(good_resp.json()['status'], 'PREPARING')

    def test_cancel_order_via_api_frees_table_and_restocks(self):
        create_resp = self.client.post('/api/orders/', data=json.dumps({
            'table': self.table.id, 'order_type': 'DINE_IN',
            'items': [{'menu_item': self.dish.id, 'quantity': 1}],
        }), content_type='application/json')
        order_id = create_resp.json()['id']

        cancel_resp = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(cancel_resp.status_code, 200)
        self.chicken.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('1000'))
        self.assertEqual(self.table.status, DiningTable.Status.AVAILABLE)
