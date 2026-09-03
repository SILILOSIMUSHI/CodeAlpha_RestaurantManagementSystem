from rest_framework import serializers
from .models import Category, MenuItem, MenuItemIngredient


class MenuItemIngredientSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    unit = serializers.CharField(source='inventory_item.unit', read_only=True)

    class Meta:
        model = MenuItemIngredient
        fields = ['id', 'inventory_item', 'inventory_item_name', 'unit', 'quantity_required']


class MenuItemSerializer(serializers.ModelSerializer):
    recipe_lines = MenuItemIngredientSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'category', 'category_name', 'name', 'description', 'price',
            'is_available', 'recipe_lines', 'created_at',
        ]
        read_only_fields = ['created_at']


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'display_order', 'item_count']
