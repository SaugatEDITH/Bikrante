from django.contrib import admin
from .models import Category, Product, Review, Order, OrderItem, UserProfile

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'discount_percentage']
    prepopulated_fields = {'slug': ('name',)}  # This auto-fills the slug field
    search_fields = ['name']
    list_filter = ['discount_percentage']

# Register other models
admin.site.register(Product)
admin.site.register(Review)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(UserProfile)