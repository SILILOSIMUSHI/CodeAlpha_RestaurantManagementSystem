from django.db import models
from django.core.validators import MinValueValidator


class InventoryItem(models.Model):
    """A raw stock item (ingredient/supply) tracked in the storeroom."""

    class Unit(models.TextChoices):
        GRAM = 'g', 'Gram'
        KILOGRAM = 'kg', 'Kilogram'
        MILLILITRE = 'ml', 'Millilitre'
        LITRE = 'l', 'Litre'
        PIECE = 'pc', 'Piece'

    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=5, choices=Unit.choices, default=Unit.PIECE)
    quantity_in_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        validators=[MinValueValidator(0)],
    )
    reorder_level = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        validators=[MinValueValidator(0)],
        help_text="Trigger a low-stock alert once quantity falls to/below this level.",
    )
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.quantity_in_stock} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.reorder_level

    def adjust_stock(self, quantity, movement_type, reason=""):
        """Apply a stock change (quantity is always positive) and log it.
        movement_type determines whether it adds to or subtracts from stock."""
        if movement_type == StockMovement.MovementType.OUT:
            if quantity > self.quantity_in_stock:
                raise ValueError(
                    f"Insufficient stock for '{self.name}': "
                    f"have {self.quantity_in_stock}{self.unit}, need {quantity}{self.unit}."
                )
            self.quantity_in_stock -= quantity
        else:
            self.quantity_in_stock += quantity
        self.save(update_fields=['quantity_in_stock', 'updated_at'])
        StockMovement.objects.create(
            inventory_item=self,
            movement_type=movement_type,
            quantity=quantity,
            reason=reason,
        )


class StockMovement(models.Model):
    """Audit trail of every stock change (sale deduction, restock, manual fix)."""

    class MovementType(models.TextChoices):
        IN = 'IN', 'Stock In'
        OUT = 'OUT', 'Stock Out'
        ADJUSTMENT = 'ADJ', 'Manual Adjustment'

    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name='movements'
    )
    movement_type = models.CharField(max_length=3, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.inventory_item.unit} - {self.inventory_item.name}"
