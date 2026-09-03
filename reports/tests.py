from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from menu.models import Category, MenuItem, MenuItemIngredient
from inventory.models import InventoryItem
from tables.models import DiningTable
from orders.models import Order
from orders import services


class ReportsApiTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name='Mains', display_order=1)
        self.chicken = InventoryItem.objects.create(
            name='Chicken', unit='g', quantity_in_stock=1000, reorder_level=1000  # at reorder level -> low stock
        )
        self.dish = MenuItem.objects.create(category=category, name='Chicken Bowl', price=Decimal('10.00'))
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.chicken, quantity_required=200)
        self.table = DiningTable.objects.create(number=1, capacity=4)

    def test_stock_alerts_lists_items_at_or_below_reorder_level(self):
        resp = self.client.get('/api/reports/stock-alerts/')
        self.assertEqual(resp.status_code, 200)
        names = [row['name'] for row in resp.json()['items']]
        self.assertIn('Chicken', names)

    def test_daily_sales_only_counts_served_or_completed_orders(self):
        order = services.place_order(
            table=self.table, order_type=Order.OrderType.DINE_IN,
            customer_name='Kai', items_data=[{'menu_item': self.dish, 'quantity': 1}],
        )
        # Still PENDING -- shouldn't count yet.
        today = timezone.localdate().isoformat()
        resp = self.client.get(f'/api/reports/daily-sales/?date={today}')
        self.assertEqual(resp.json()['order_count'], 0)

        services.complete_order(order)
        resp = self.client.get(f'/api/reports/daily-sales/?date={today}')
        body = resp.json()
        self.assertEqual(body['order_count'], 1)
        self.assertEqual(Decimal(str(body['total_revenue'])), Decimal('10.00'))
        self.assertEqual(body['top_selling_items'][0]['menu_item__name'], 'Chicken Bowl')
