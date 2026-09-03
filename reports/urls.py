from django.urls import path
from . import views

urlpatterns = [
    path('daily-sales/', views.daily_sales, name='report-daily-sales'),
    path('sales-range/', views.sales_range, name='report-sales-range'),
    path('stock-alerts/', views.stock_alerts, name='report-stock-alerts'),
]
