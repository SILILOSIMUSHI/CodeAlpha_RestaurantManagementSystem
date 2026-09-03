"""Order-processing business logic: table availability, stock checks,
inventory auto-deduction. Kept separate from views/serializers so it can be
reused (e.g. from the add-item action) and unit tested in isolation."""
from django.db import transaction
from django.core.exceptions import ValidationError

from tables.models import DiningTable
from .models import Order, OrderItem


def check_table_available(table):
    if table.status != DiningTable.Status.AVAILABLE:
        raise ValidationError(
            f"Table {table.number} is not available (currently {table.get_status_display()})."
        )


def check_items_in_stock(items_data):
    """items_data: list of dicts with 'menu_item' (MenuItem instance) and 'quantity'.
    Raises ValidationError naming the first item/ingredient that can't be fulfilled."""
    for line in items_data:
        menu_item = line['menu_item']
        quantity = line['quantity']
        if not menu_item.is_available:
            raise ValidationError(f"'{menu_item.name}' is currently unavailable.")
        ok, short_ingredient = menu_item.has_sufficient_stock(quantity)
        if not ok:
            raise ValidationError(
                f"Not enough '{short_ingredient.name}' in stock to make {quantity} x {menu_item.name}."
            )


@transaction.atomic
def place_order(*, table, order_type, customer_name, items_data):
    """Creates the order with its items, deducts inventory for each item, and
    (for dine-in) marks the table occupied. items_data: list of dicts with
    menu_item, quantity, special_instructions."""
    if order_type == Order.OrderType.DINE_IN and table is not None:
        check_table_available(table)

    check_items_in_stock(items_data)

    order = Order.objects.create(
        table=table if order_type == Order.OrderType.DINE_IN else None,
        order_type=order_type,
        customer_name=customer_name,
        status=Order.Status.PENDING,
    )

    for line in items_data:
        menu_item = line['menu_item']
        quantity = line['quantity']
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            unit_price=menu_item.price,
            special_instructions=line.get('special_instructions', ''),
        )
        menu_item.deduct_stock_for_order(quantity=quantity, reason=f"Order #{order.pk}")

    if order.order_type == Order.OrderType.DINE_IN and order.table is not None:
        order.table.status = DiningTable.Status.OCCUPIED
        order.table.save(update_fields=['status'])

    return order


@transaction.atomic
def add_item_to_order(*, order, menu_item, quantity, special_instructions=""):
    if order.status in (Order.Status.COMPLETED, Order.Status.CANCELLED):
        raise ValidationError(f"Can't add items to a {order.get_status_display().lower()} order.")

    check_items_in_stock([{'menu_item': menu_item, 'quantity': quantity}])

    item = OrderItem.objects.create(
        order=order,
        menu_item=menu_item,
        quantity=quantity,
        unit_price=menu_item.price,
        special_instructions=special_instructions,
    )
    menu_item.deduct_stock_for_order(quantity=quantity, reason=f"Order #{order.pk} (added item)")
    return item


@transaction.atomic
def complete_order(order):
    order.status = Order.Status.COMPLETED
    order.save(update_fields=['status', 'updated_at'])
    if order.table is not None:
        order.table.status = DiningTable.Status.AVAILABLE
        order.table.save(update_fields=['status'])
    return order


@transaction.atomic
def cancel_order(order, restock=True):
    """Cancel an order. By default restocks any inventory already deducted."""
    if restock:
        for item in order.items.select_related('menu_item').all():
            item.menu_item.recipe_lines_qs = item.menu_item.recipe_lines.select_related('inventory_item').all()
            for recipe_line in item.menu_item.recipe_lines_qs:
                recipe_line.inventory_item.adjust_stock(
                    quantity=recipe_line.quantity_required * item.quantity,
                    movement_type='IN',
                    reason=f"Order #{order.pk} cancelled - restock",
                )
    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    if order.table is not None:
        order.table.status = DiningTable.Status.AVAILABLE
        order.table.save(update_fields=['status'])
    return order
