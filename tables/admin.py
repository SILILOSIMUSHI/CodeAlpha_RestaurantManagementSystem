from django.contrib import admin
from .models import DiningTable, Reservation


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ('number', 'capacity', 'status')
    list_filter = ('status',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'table', 'party_size', 'reservation_time', 'status')
    list_filter = ('status', 'reservation_time')
    search_fields = ('customer_name', 'customer_phone')
