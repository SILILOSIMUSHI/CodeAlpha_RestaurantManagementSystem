from django.db import models
from django.core.validators import MinValueValidator
from inventory.models import InventoryItem


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category__display_order', 'name']

    def __str__(self):
        return self.name

    def has_sufficient_stock(self, quantity=1):
        """Check every recipe ingredient has enough inventory for `quantity` servings."""
        for recipe_line in self.recipe_lines.select_related('inventory_item').all():
            required = recipe_line.quantity_required * quantity
            if required > recipe_line.inventory_item.quantity_in_stock:
                return False, recipe_line.inventory_item
        return True, None

    def deduct_stock_for_order(self, quantity=1, reason=""):
        """Deduct each ingredient's required amount from inventory for `quantity` servings."""
        for recipe_line in self.recipe_lines.select_related('inventory_item').all():
            recipe_line.inventory_item.adjust_stock(
                quantity=recipe_line.quantity_required * quantity,
                movement_type='OUT',
                reason=reason or f"Sold: {self.name} x{quantity}",
            )


class MenuItemIngredient(models.Model):
    """Recipe line: how much of an inventory item one serving of a menu item needs.
    This is what powers automatic inventory deduction when an order is placed."""

    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='recipe_lines')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='used_in')
    quantity_required = models.DecimalField(
        max_digits=10, decimal_places=3,
        help_text="Amount of the inventory item's unit needed per one serving.",
    )

    class Meta:
        unique_together = ('menu_item', 'inventory_item')

    def __str__(self):
        return f"{self.menu_item.name}: {self.quantity_required}{self.inventory_item.unit} {self.inventory_item.name}"
