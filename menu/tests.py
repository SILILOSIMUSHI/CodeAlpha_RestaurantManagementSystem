from decimal import Decimal
from django.test import TestCase
from .models import Category, MenuItem, MenuItemIngredient
from inventory.models import InventoryItem


class MenuItemStockTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Mains', display_order=1)
        self.chicken = InventoryItem.objects.create(name='Chicken', unit='g', quantity_in_stock=1000, reorder_level=100)
        self.rice = InventoryItem.objects.create(name='Rice', unit='g', quantity_in_stock=2000, reorder_level=200)
        self.dish = MenuItem.objects.create(category=self.category, name='Chicken Bowl', price=Decimal('10.00'))
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.chicken, quantity_required=200)
        MenuItemIngredient.objects.create(menu_item=self.dish, inventory_item=self.rice, quantity_required=150)

    def test_has_sufficient_stock_true_when_enough(self):
        ok, shortfall = self.dish.has_sufficient_stock(quantity=3)
        self.assertTrue(ok)
        self.assertIsNone(shortfall)

    def test_has_sufficient_stock_false_when_ingredient_short(self):
        ok, shortfall = self.dish.has_sufficient_stock(quantity=10)  # needs 2000g chicken, only have 1000g
        self.assertFalse(ok)
        self.assertEqual(shortfall, self.chicken)

    def test_deduct_stock_for_order_reduces_each_ingredient(self):
        self.dish.deduct_stock_for_order(quantity=2)
        self.chicken.refresh_from_db()
        self.rice.refresh_from_db()
        self.assertEqual(self.chicken.quantity_in_stock, Decimal('600'))   # 1000 - 400
        self.assertEqual(self.rice.quantity_in_stock, Decimal('1700'))     # 2000 - 300


class MenuApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Drinks', display_order=1)
        MenuItem.objects.create(category=self.category, name='Cola', price=Decimal('2.50'), is_available=True)
        MenuItem.objects.create(category=self.category, name='Retired Item', price=Decimal('1.00'), is_available=False)

    def test_list_items(self):
        resp = self.client.get('/api/menu/items/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']) if 'results' in resp.json() else len(resp.json()), 2)

    def test_filter_available_items(self):
        resp = self.client.get('/api/menu/items/?available=true')
        data = resp.json()
        rows = data['results'] if 'results' in data else data
        names = [row['name'] for row in rows]
        self.assertIn('Cola', names)
        self.assertNotIn('Retired Item', names)
