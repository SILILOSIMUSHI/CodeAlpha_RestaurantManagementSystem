from django.db import models
from django.core.validators import MinValueValidator
from menu.models import MenuItem
from tables.models import DiningTable


class Order(models.Model):
    class OrderType(models.TextChoices):
        DINE_IN = 'DINE_IN', 'Dine-in'
        TAKEAWAY = 'TAKEAWAY', 'Takeaway'
        DELIVERY = 'DELIVERY', 'Delivery'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PREPARING = 'PREPARING', 'Preparing'
        READY = 'READY', 'Ready'
        SERVED = 'SERVED', 'Served'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    table = models.ForeignKey(
        DiningTable, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    order_type = models.CharField(max_length=10, choices=OrderType.choices, default=OrderType.DINE_IN)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    customer_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.pk} ({self.get_status_display()})"

    @property
    def total_amount(self):
        return sum((item.subtotal for item in self.items.all()), start=0)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    special_instructions = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.menu_item.price
        super().save(*args, **kwargs)
