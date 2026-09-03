from rest_framework import serializers
from menu.models import MenuItem
from tables.models import DiningTable
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'menu_item', 'menu_item_name', 'quantity', 'unit_price',
            'special_instructions', 'subtotal',
        ]
        read_only_fields = ['unit_price']


class OrderItemInputSerializer(serializers.Serializer):
    """Used only for nested write input on order creation / add-item."""
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)
    special_instructions = serializers.CharField(required=False, allow_blank=True, default="")


class OrderSerializer(serializers.ModelSerializer):
    """Read serializer, with nested items."""
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    table_number = serializers.IntegerField(source='table.number', read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            'id', 'table', 'table_number', 'order_type', 'status', 'customer_name',
            'items', 'total_amount', 'created_at', 'updated_at',
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.Serializer):
    """Write serializer: validates and places a new order via orders.services.place_order."""
    table = serializers.PrimaryKeyRelatedField(queryset=DiningTable.objects.all(), required=False, allow_null=True)
    order_type = serializers.ChoiceField(choices=Order.OrderType.choices, default=Order.OrderType.DINE_IN)
    customer_name = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderItemInputSerializer(many=True)

    def validate(self, attrs):
        if attrs.get('order_type') == Order.OrderType.DINE_IN and not attrs.get('table'):
            raise serializers.ValidationError("A table is required for dine-in orders.")
        if not attrs.get('items'):
            raise serializers.ValidationError("An order needs at least one item.")
        return attrs
