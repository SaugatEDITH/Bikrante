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
##! for word like gui type text typing (if also image upload required un comment below and comment up one)
from ckeditor.fields import RichTextField
## from ckeditor_uploader.fields import RichTextUploadingField
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
    category_discount_apply=models.BooleanField(
        default=False,
        help_text="Enable discount application for products in this category"
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
    id=models.AutoField(primary_key=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_applied=models.BooleanField(default=False,help_text="Apply discount to this product")
    price_after_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # New Field
    
    brand_name=models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated tags e.g.(tech, makeup, education, etc..)",
    )
    stock = models.IntegerField()
    availability = models.BooleanField(default=True)
    colors = models.CharField(
        max_length=255, blank=True, help_text="Comma seperated colors e.g.()"
    )
    sizes = models.CharField(max_length=255, blank=True,help_text="Comma seperated sizes e.g.(xl, xxl, l, ml etc)")
    image1 = models.ImageField(upload_to="product_images/")
    image2 = models.ImageField(upload_to="product_images/")
    image3 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    image4 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    image5 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    image6 = models.ImageField(upload_to="product_images/", null=True, blank=True)
    likes = models.ManyToManyField(User, related_name="liked_products", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)  # Add slug field
    is_hot = models.BooleanField(default=False)
    ##! for word like gui type text typing
    specifications = RichTextField(null=True, blank=True,help_text="Enter table class name as :info__table")
    views_count = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0)
    last_viewed = models.DateTimeField(null=True, blank=True)
 
    def __str__(self):
        return self.name

    def get_discounted_price(self):
        """
        Calculate the discounted price based on category discount settings
        """
        if self.discount_applied and self.category.category_discount_apply:
            discount_amount = (self.price * self.category.discount_percentage) / 100
            return round(self.price - discount_amount, 2)
        return self.price

    def update_discount_price(self):
        """
        Updates the stored price_after_discount based on category settings
        """
        self.price_after_discount = self.get_discounted_price()

    def save(self, *args, **kwargs):
        # Calculate and update the discounted price
        self.update_discount_price()
        
        if not self.slug:
            base_slug = generate_slug(self.name)
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = unique_slug
            
        super().save(*args, **kwargs)

    
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
    visible=models.BooleanField(default=True)
    ip=models.CharField(max_length=20,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s review on {self.product.name}"
    @classmethod
    def get_client_ip(request):
        """Returns the real IP address of the user."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]  # Get the first IP in the list
        else:
            ip = request.META.get('REMOTE_ADDR')  # Fallback to direct IP
        return ip


#  Orders
class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, through="OrderItem")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_price = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    payment=models.BooleanField(default=False)
    # 🔹 Billing Details
    customer_name = models.CharField(max_length=255,default="Default User")
    customer_address = models.TextField(default="Unknown Address")
    city = models.CharField(max_length=100,null=True)
    postcode = models.CharField(max_length=20,null=True)
    phone = models.CharField(max_length=20,null=True)
    customer_email = models.EmailField(null=True)
    order_note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"
        
class OrderItem(models.Model):  # Changed from OrderItems to OrderItem
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class CartItem(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name="cart_items")
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)
    added_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    def total_price(self):
        return (self.product.price_after_discount or self.product.price)*self.quantity
    
        
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_image = models.ImageField(
        upload_to="profile_images/",
        default='profile_pictures/defaultprofile.png' ,
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Success", "Success"),
        ("Failed", "Failed"),
    ]

    PAYMENT_METHODS = [
        ("Esewa", "Esewa"),
        ("Khalti", "Khalti"),  # Add if supporting more gateways later
        ("Cash on Delivery", "Cash on Delivery"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default="Esewa")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    esewa_transaction_id = models.CharField(max_length=50, blank=True, null=True, help_text="eSewa Txn ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Txn {self.esewa_transaction_id} - {self.status}"
