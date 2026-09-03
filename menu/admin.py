from django.contrib import admin
from .models import Category, MenuItem, MenuItemIngredient


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order')
    ordering = ('display_order',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)
    inlines = [MenuItemIngredientInline]
