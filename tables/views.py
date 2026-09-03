from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DiningTable, Reservation
from .serializers import DiningTableSerializer, ReservationSerializer


class DiningTableViewSet(viewsets.ModelViewSet):
    queryset = DiningTable.objects.all()
    serializer_class = DiningTableSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        """Tables currently free to seat walk-ins, optionally filtered by min party size."""
        qs = self.get_queryset().filter(status=DiningTable.Status.AVAILABLE)
        party_size = request.query_params.get('party_size')
        if party_size:
            qs = qs.filter(capacity__gte=int(party_size))
        return Response(self.get_serializer(qs, many=True).data)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related('table').all()
    serializer_class = ReservationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        table = self.request.query_params.get('table')
        if table:
            qs = qs.filter(table_id=table)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def perform_create(self, serializer):
        reservation = serializer.save(status=Reservation.Status.CONFIRMED)
        reservation.table.status = DiningTable.Status.RESERVED
        reservation.table.save(update_fields=['status'])

    @action(detail=True, methods=['post'], url_path='seat')
    def seat(self, request, pk=None):
        """Mark the guests as seated; table becomes occupied."""
        reservation = self.get_object()
        reservation.status = Reservation.Status.SEATED
        reservation.save(update_fields=['status'])
        reservation.table.status = DiningTable.Status.OCCUPIED
        reservation.table.save(update_fields=['status'])
        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Guests have left; free up the table."""
        reservation = self.get_object()
        reservation.status = Reservation.Status.COMPLETED
        reservation.save(update_fields=['status'])
        reservation.table.status = DiningTable.Status.AVAILABLE
        reservation.table.save(update_fields=['status'])
        return Response(self.get_serializer(reservation).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        reservation.status = Reservation.Status.CANCELLED
        reservation.save(update_fields=['status'])
        if reservation.table.status == DiningTable.Status.RESERVED:
            reservation.table.status = DiningTable.Status.AVAILABLE
            reservation.table.save(update_fields=['status'])
        return Response(self.get_serializer(reservation).data)
