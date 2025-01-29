from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import re
from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta
from django.core.files.storage import default_storage
from django.core.files import File
import os
from django.urls import reverse

def generate_slug(title):
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower().strip().replace(' ', '-')
    
    # Remove special characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Replace multiple consecutive hyphens with a single hyphen
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading and trailing hyphens
    slug = slug.strip('-')
    
    return slug

# Create your models here.


# Product Category
class Category(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to='categories',
        null=True,
        blank=True,
        help_text="Upload category image (Recommended: 300x300px)"
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text="Leave empty for automatic generation from name"
    )  # Remove null=True as it's not needed with blank=True
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Discount percentage for all products in this category (e.g., 10 for 10%)",
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:  # Only generate slug if it's empty
            self.slug = generate_slug(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category-detail', kwargs={'slug': self.slug})

    def get_image_url(self):
        """Returns the URL of the image or default image if none exists"""
        try:
            return self.image.url if self.image else None
        except:
            return None


# Product
class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=100, unique=True)
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-seperated tags e.g.(tech,makup,education etc..)",
    )
    stock = models.IntegerField()
    availability = models.BooleanField(default=True)
    colors = models.CharField(
        max_length=255, blank=True, help_text="Comma seperated colors e.g.()"
    )
    sizes = models.CharField(max_length=255, blank=True)
    image1 = models.ImageField(upload_to="product_images/")
    image2 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    image3 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    image4 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    likes = models.ManyToManyField(User, related_name="liked_products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)  # Add slug field
    is_hot = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def get_discounted_price(self):
        """
        Dynamically calculates the discounted price based on the catagory's discount percentage.
        """
        if self.category.discount_percentage > 0:
            discount_amount = (self.price * self.category.discount_percentage) / 100
            return round(self.price - discount_amount, 2)
        return self.price

    def total_likes(self):
        """
        Returns the total number of likes for the product
        """
        return self.likes.count()
    # unique slug generator
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = generate_slug(self.name)
            # Check for existing slugs
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)

    @classmethod
    def get_hot_products(cls, limit=4):
        """Products manually marked as hot deals"""
        return cls.objects.filter(is_hot=True)[:limit]
    
    @classmethod
    def get_trending_products(cls, days=7, limit=4):
        """Products with most views in last 7 days"""
        date_threshold = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            last_viewed__gte=date_threshold
        ).order_by('-views_count')[:limit]

    @classmethod
    def get_new_arrivals(cls, days=30, limit=4):
        """Products added in last 30 days"""
        date_threshold = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            created_at__gte=date_threshold
        ).order_by('-created_at')[:limit]

    @classmethod
    def get_top_selling(cls, limit=4):
        """Products with highest sales count"""
        return cls.objects.order_by('-sales_count')[:limit]

    @classmethod
    def get_popular_products(cls, limit=4):
        """Products with most likes"""
        return cls.objects.annotate(
            like_count=Count('likes')
        ).order_by('-like_count')[:limit]

    def get_cross_sell_products(self, limit=4):
        """Products from same category that others bought"""
        return Product.objects.filter(
            category=self.category
        ).exclude(id=self.id).order_by('-sales_count')[:limit]

    def get_upsell_products(self, limit=4):
        """More expensive products in same category"""
        return Product.objects.filter(
            category=self.category,
            price__gt=self.price
        ).order_by('price')[:limit]

    def increment_views(self):
        """Increment view count when product is viewed"""
        self.views_count += 1
        self.last_viewed = timezone.now()
        self.save()

    def record_sale(self, quantity=1):
        """Record a sale of the product"""
        self.sales_count += quantity
        self.save()


#  Reviews


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        default=None,
    )

    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s review on {self.product.name}"


#  Orders
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    product = models.ManyToManyField(Product, through="OrderItem")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ("Pending", "Pending"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled"),
        ],
        default="Pending",
    )

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"


class OrderItem(models.Model):  # Changed from OrderItems to OrderItem
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(
        upload_to="profile_images/", null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"
