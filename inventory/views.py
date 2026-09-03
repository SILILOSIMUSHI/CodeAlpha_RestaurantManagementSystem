from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import InventoryItem, StockMovement
from .serializers import InventoryItemSerializer, StockMovementSerializer, StockAdjustmentSerializer


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer

    @action(detail=False, methods=['get'], url_path='low-stock')
    def low_stock(self, request):
        """Items at or below their reorder level -- for stock alerts."""
        items = [item for item in self.get_queryset() if item.is_low_stock]
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='adjust-stock')
    def adjust_stock(self, request, pk=None):
        """Manually restock or correct an inventory item, logging the movement."""
        item = self.get_object()
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item.adjust_stock(
                quantity=data['quantity'],
                movement_type=data['movement_type'],
                reason=data.get('reason', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InventoryItemSerializer(item).data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit log of stock movements."""
    queryset = StockMovement.objects.select_related('inventory_item').all()
    serializer_class = StockMovementSerializer
