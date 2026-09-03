from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer, OrderItemInputSerializer
from . import services


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('table').prefetch_related('items__menu_item').all()
    serializer_class = OrderSerializer
    http_method_names = ['get', 'post', 'head', 'options']  # updates go through actions below

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        order_type = self.request.query_params.get('order_type')
        if order_type:
            qs = qs.filter(order_type=order_type.upper())
        return qs

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            order = services.place_order(
                table=data.get('table'),
                order_type=data['order_type'],
                customer_name=data.get('customer_name', ''),
                items_data=data['items'],
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages[0] if hasattr(exc, 'messages') else str(exc)},
                             status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
        order = self.get_object()
        item_serializer = OrderItemInputSerializer(data=request.data)
        item_serializer.is_valid(raise_exception=True)
        data = item_serializer.validated_data
        try:
            services.add_item_to_order(
                order=order,
                menu_item=data['menu_item'],
                quantity=data['quantity'],
                special_instructions=data.get('special_instructions', ''),
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages[0] if hasattr(exc, 'messages') else str(exc)},
                             status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None):
        """Advance status through PENDING -> PREPARING -> READY -> SERVED."""
        order = self.get_object()
        new_status = request.data.get('status', '').upper()
        valid_transitions = {
            Order.Status.PENDING: [Order.Status.PREPARING, Order.Status.CANCELLED],
            Order.Status.PREPARING: [Order.Status.READY, Order.Status.CANCELLED],
            Order.Status.READY: [Order.Status.SERVED],
            Order.Status.SERVED: [Order.Status.COMPLETED],
        }
        if new_status not in Order.Status.values:
            return Response({'detail': f"'{new_status}' is not a valid status."}, status=400)
        allowed = valid_transitions.get(order.status, [])
        if new_status not in allowed and order.status not in (Order.Status.COMPLETED, Order.Status.CANCELLED):
            return Response(
                {'detail': f"Can't move order from {order.status} to {new_status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_status == Order.Status.COMPLETED:
            services.complete_order(order)
        elif new_status == Order.Status.CANCELLED:
            services.cancel_order(order)
        else:
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        order = self.get_object()
        services.complete_order(order)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        order = self.get_object()
        services.cancel_order(order)
        return Response(OrderSerializer(order).data)
