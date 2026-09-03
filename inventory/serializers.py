from decimal import Decimal
from rest_framework import serializers
from .models import InventoryItem, StockMovement


class StockMovementSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'inventory_item', 'inventory_item_name', 'movement_type',
            'quantity', 'reason', 'created_at',
        ]
        read_only_fields = ['created_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'name', 'unit', 'quantity_in_stock', 'reorder_level',
            'cost_per_unit', 'is_low_stock', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """Used by the restock/adjust-stock action on InventoryItemViewSet."""
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    movement_type = serializers.ChoiceField(choices=StockMovement.MovementType.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
