from rest_framework import viewsets
from .models import Category, MenuItem, MenuItemIngredient
from .serializers import CategorySerializer, MenuItemSerializer, MenuItemIngredientSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related('category').prefetch_related('recipe_lines__inventory_item').all()
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        available = self.request.query_params.get('available')
        if available is not None:
            qs = qs.filter(is_available=(available.lower() == 'true'))
        category = self.request.query_params.get('category')
        if category is not None:
            qs = qs.filter(category_id=category)
        return qs


class MenuItemIngredientViewSet(viewsets.ModelViewSet):
    """Manage the recipe (ingredient list) behind each menu item."""
    queryset = MenuItemIngredient.objects.select_related('menu_item', 'inventory_item').all()
    serializer_class = MenuItemIngredientSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        menu_item = self.request.query_params.get('menu_item')
        if menu_item is not None:
            qs = qs.filter(menu_item_id=menu_item)
        return qs
