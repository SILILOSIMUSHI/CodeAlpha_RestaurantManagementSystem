from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_type', 'table', 'status', 'customer_name', 'total_amount', 'created_at')
    list_filter = ('status', 'order_type', 'created_at')
    search_fields = ('customer_name',)
    inlines = [OrderItemInline]

    @admin.display(description='Total')
    def total_amount(self, obj):
        return obj.total_amount
