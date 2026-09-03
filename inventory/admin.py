from django.contrib import admin
from .models import InventoryItem, StockMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'quantity_in_stock', 'reorder_level', 'cost_per_unit', 'is_low_stock')
    list_filter = ('unit',)
    search_fields = ('name',)

    @admin.display(boolean=True, description='Low stock')
    def is_low_stock(self, obj):
        return obj.is_low_stock


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'movement_type', 'quantity', 'reason', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('inventory_item__name', 'reason')
