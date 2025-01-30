from django.contrib import admin
from .models import Category, Product, Review, Order, OrderItem, UserProfile

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'image', 'slug', 'discount_percentage']
    list_display_links = ['name']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_filter = ['discount_percentage']
    list_editable = ['discount_percentage']
    ordering = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'description',
        'price',
        'brand_name',
        'sku',
        'tags',
        'stock',
        'availability',
        'colors',
        'sizes',
        'is_hot',
        'sales_count',
        'views_count',
        'created_at',
        'last_viewed',
        'slug'
    ]
    list_display_links = ['name', 'sku']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['category', 'availability', 'is_hot', 'created_at','brand_name']
    search_fields = ['name', 'description', 'sku', 'tags']
    list_editable = ['price', 'stock', 'availability', 'is_hot', 'colors', 'sizes']
    readonly_fields = ['views_count', 'sales_count', 'last_viewed', 'created_at']
    list_per_page = 20
    ordering = ['-created_at']

# Register other models
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(UserProfile)