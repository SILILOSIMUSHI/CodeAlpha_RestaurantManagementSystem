from decimal import Decimal
from django.core.management.base import BaseCommand

from menu.models import Category, MenuItem, MenuItemIngredient
from inventory.models import InventoryItem
from tables.models import DiningTable


class Command(BaseCommand):
    help = "Populate the database with sample categories, menu items, inventory, and tables for demo/testing."

    def handle(self, *args, **options):
        if Category.objects.exists():
            self.stdout.write(self.style.WARNING("Demo data already present -- skipping."))
            return

        chicken = InventoryItem.objects.create(name='Chicken Breast', unit='g', quantity_in_stock=5000, reorder_level=1000, cost_per_unit=Decimal('0.02'))
        rice = InventoryItem.objects.create(name='Rice', unit='g', quantity_in_stock=8000, reorder_level=2000, cost_per_unit=Decimal('0.005'))
        tomato = InventoryItem.objects.create(name='Tomato', unit='g', quantity_in_stock=3000, reorder_level=800, cost_per_unit=Decimal('0.01'))
        cheese = InventoryItem.objects.create(name='Mozzarella', unit='g', quantity_in_stock=2000, reorder_level=500, cost_per_unit=Decimal('0.03'))
        dough = InventoryItem.objects.create(name='Pizza Dough', unit='pc', quantity_in_stock=40, reorder_level=10, cost_per_unit=Decimal('0.50'))
        cola = InventoryItem.objects.create(name='Cola Syrup', unit='ml', quantity_in_stock=3000, reorder_level=500, cost_per_unit=Decimal('0.01'))

        mains = Category.objects.create(name='Mains', display_order=1)
        pizzas = Category.objects.create(name='Pizzas', display_order=2)
        drinks = Category.objects.create(name='Drinks', display_order=3)

        bowl = MenuItem.objects.create(category=mains, name='Chicken Rice Bowl', description='Grilled chicken over seasoned rice.', price=Decimal('12.50'))
        MenuItemIngredient.objects.create(menu_item=bowl, inventory_item=chicken, quantity_required=200)
        MenuItemIngredient.objects.create(menu_item=bowl, inventory_item=rice, quantity_required=150)

        margherita = MenuItem.objects.create(category=pizzas, name='Margherita Pizza', description='Tomato, mozzarella, basil.', price=Decimal('10.00'))
        MenuItemIngredient.objects.create(menu_item=margherita, inventory_item=dough, quantity_required=1)
        MenuItemIngredient.objects.create(menu_item=margherita, inventory_item=tomato, quantity_required=150)
        MenuItemIngredient.objects.create(menu_item=margherita, inventory_item=cheese, quantity_required=120)

        soda = MenuItem.objects.create(category=drinks, name='Cola', description='Fountain cola.', price=Decimal('2.50'))
        MenuItemIngredient.objects.create(menu_item=soda, inventory_item=cola, quantity_required=250)

        for n, cap in [(1, 2), (2, 4), (3, 4), (4, 6), (5, 2)]:
            DiningTable.objects.create(number=n, capacity=cap)

        self.stdout.write(self.style.SUCCESS(
            "Seeded 3 categories, 3 menu items, 6 inventory items, 5 tables."
        ))
