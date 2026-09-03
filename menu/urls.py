from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, MenuItemViewSet, MenuItemIngredientViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('items', MenuItemViewSet, basename='menu-item')
router.register('recipe-lines', MenuItemIngredientViewSet, basename='menu-item-ingredient')

urlpatterns = router.urls
