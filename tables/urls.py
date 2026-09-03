from rest_framework.routers import DefaultRouter
from .views import DiningTableViewSet, ReservationViewSet

router = DefaultRouter()
router.register('tables', DiningTableViewSet, basename='dining-table')
router.register('reservations', ReservationViewSet, basename='reservation')

urlpatterns = router.urls
