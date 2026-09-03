from datetime import datetime, timedelta

from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from orders.models import Order, OrderItem
from inventory.models import InventoryItem
from inventory.serializers import InventoryItemSerializer


def _parse_date(request, param='date'):
    raw = request.query_params.get(param)
    if raw:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    return timezone.localdate()


@api_view(['GET'])
def daily_sales(request):
    """Sales report for a single day (?date=YYYY-MM-DD, defaults to today).
    Only counts completed/served orders as realised sales."""
    day = _parse_date(request)
    orders = Order.objects.filter(
        created_at__date=day,
        status__in=[Order.Status.SERVED, Order.Status.COMPLETED],
    )
    items = OrderItem.objects.filter(order__in=orders)

    total_revenue = items.aggregate(
        total=Coalesce(
            Sum(F('unit_price') * F('quantity'), output_field=DecimalField()),
            0,
            output_field=DecimalField(),
        )
    )['total']

    top_items = (
        items.values('menu_item__name')
        .annotate(units_sold=Sum('quantity'))
        .order_by('-units_sold')[:5]
    )

    return Response({
        'date': str(day),
        'order_count': orders.count(),
        'total_revenue': total_revenue,
        'top_selling_items': list(top_items),
    })


@api_view(['GET'])
def sales_range(request):
    """Sales grouped by day across a range: ?start=YYYY-MM-DD&end=YYYY-MM-DD."""
    end = _parse_date(request, 'end')
    start_raw = request.query_params.get('start')
    start = datetime.strptime(start_raw, '%Y-%m-%d').date() if start_raw else end - timedelta(days=6)

    orders = Order.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
        status__in=[Order.Status.SERVED, Order.Status.COMPLETED],
    )
    items = OrderItem.objects.filter(order__in=orders).annotate(day=TruncDate('order__created_at'))

    daily = (
        items.values('day')
        .annotate(revenue=Sum(F('unit_price') * F('quantity'), output_field=DecimalField()))
        .order_by('day')
    )
    return Response({'start': str(start), 'end': str(end), 'daily_revenue': list(daily)})


@api_view(['GET'])
def stock_alerts(request):
    """Inventory items at or below their reorder level."""
    low_items = [item for item in InventoryItem.objects.all() if item.is_low_stock]
    return Response({
        'count': len(low_items),
        'items': InventoryItemSerializer(low_items, many=True).data,
    })
