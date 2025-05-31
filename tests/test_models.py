import os
import sys

# Ensure project root is in sys.path and DJANGO_SETTINGS_MODULE is set
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Bikrante.settings")

import django
django.setup()

import pytest
from django.contrib.auth.models import User
from shopapp.models import (
    Category, Product, Review, Order, OrderItem, CartItem, UserProfile, Transaction, CategoryDeal
)
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_category_slug_generation():
    import uuid
    unique_name = f"Test Category {uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name)
    assert cat.slug.startswith("test-category")
    assert str(cat) == unique_name

@pytest.mark.django_db
def test_category_discount_and_image_url():
    import uuid
    unique_name = f"Discount Cat {uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name, discount_percentage=10)
    assert cat.discount_percentage == Decimal("10")
    assert cat.get_image_url() is not None

@pytest.mark.django_db
def test_product_creation_and_discount():
    # Use a unique category name to avoid slug collision
    import uuid
    unique_name = f"Electronics-{uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name, discount_percentage=20, category_discount_apply=True)
    prod = Product.objects.create(
        category=cat,
        name="Laptop",
        description="A good laptop",
        price=Decimal("1000"),
        discount_applied=True,
        brand_name="BrandX",
        sku="SKU123",
        stock=10,
        availability=True,
        colors="red,blue",
        sizes="M,L",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    assert prod.get_discounted_price() == Decimal("800")
    assert prod.price_after_discount == Decimal("800")
    assert prod.slug.startswith("laptop")
    assert str(prod) == "Laptop"
    assert prod.get_colors() == ["red", "blue"]
    assert prod.get_sizes() == ["M", "L"]

@pytest.mark.django_db
def test_product_star_rating_and_methods():
    import uuid
    unique_name = f"Books {uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name)
    prod = Product.objects.create(
        category=cat,
        name="Book",
        description="A book",
        price=Decimal("50"),
        discount_applied=False,
        brand_name="BrandB",
        sku="SKU456",
        stock=5,
        availability=True,
        colors="green",
        sizes="S",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    user = User.objects.create_user(username=f"user1_{uuid.uuid4()}", password="pass")
    Review.objects.create(product=prod, user=user, rating=4)
    assert prod.calculate_star_rating() == ["⭐", "⭐", "⭐", "⭐"]
    prod.increment_views()
    assert prod.views_count == 1
    prod.record_sale(2)
    assert prod.sales_count == 2

@pytest.mark.django_db
def test_review_str_and_ip():
    import uuid
    unique_name = f"Cat {uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name)
    prod = Product.objects.create(
        category=cat,
        name="Prod",
        description="desc",
        price=Decimal("10"),
        discount_applied=False,
        brand_name="Brand",
        sku="SKU789",
        stock=1,
        availability=True,
        colors="",
        sizes="",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    user = User.objects.create_user(username=f"user2_{uuid.uuid4()}", password="pass")
    review = Review.objects.create(product=prod, user=user, rating=5)
    assert str(review) == f"{user.username}'s review on Prod"

@pytest.mark.django_db
def test_order_and_orderitem_save_and_str():
    import uuid
    user = User.objects.create_user(username=f"orderuser_{uuid.uuid4()}", password="pass")
    cat = Category.objects.create(name=f"OrderCat {uuid.uuid4()}")
    prod = Product.objects.create(
        category=cat,
        name="OrderProd",
        description="desc",
        price=Decimal("20"),
        discount_applied=False,
        brand_name="Brand",
        sku="SKU321",
        stock=10,
        availability=True,
        colors="",
        sizes="",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    order = Order.objects.create(
        user=user,
        total_price=Decimal("20"),
        shipping_price=Decimal("5"),
        customer_name="Test User",
        customer_address="Test Address",
        city="Test City",
        postcode="12345",
        phone="1234567890",
        customer_email="test@example.com"
    )
    item = OrderItem.objects.create(order=order, product=prod, quantity=2, price=Decimal("40"))
    assert str(item) == "2 x OrderProd"
    assert str(order) == f"Order #{order.id} by {user.username}"

@pytest.mark.django_db
def test_cartitem_total_price():
    import uuid
    user = User.objects.create_user(username=f"cartuser_{uuid.uuid4()}", password="pass")
    cat = Category.objects.create(name=f"CartCat {uuid.uuid4()}")
    prod = Product.objects.create(
        category=cat,
        name="CartProd",
        description="desc",
        price=Decimal("30"),
        discount_applied=False,
        brand_name="Brand",
        sku="SKU654",
        stock=10,
        availability=True,
        colors="",
        sizes="",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    cart_item = CartItem.objects.create(user=user, product=prod, quantity=3)
    assert cart_item.total_price() == Decimal("90")
    assert str(cart_item) == "3 x CartProd"

@pytest.mark.django_db
def test_userprofile_str():
    import uuid
    user = User.objects.create_user(username=f"profileuser_{uuid.uuid4()}", password="pass")
    profile = UserProfile.objects.create(user=user, address="Addr", phone_number="123")
    assert str(profile) == f"{user.username}'s Profile"

@pytest.mark.django_db
def test_transaction_str():
    import uuid
    user = User.objects.create_user(username=f"txnuser_{uuid.uuid4()}", password="pass")
    cat = Category.objects.create(name=f"TxnCat {uuid.uuid4()}")
    prod = Product.objects.create(
        category=cat,
        name="TxnProd",
        description="desc",
        price=Decimal("50"),
        discount_applied=False,
        brand_name="Brand",
        sku="SKU987",
        stock=10,
        availability=True,
        colors="",
        sizes="",
        image1=SimpleUploadedFile("img1.jpg", b"file_content"),
        image2=SimpleUploadedFile("img2.jpg", b"file_content"),
    )
    order = Order.objects.create(
        user=user,
        total_price=Decimal("50"),
        shipping_price=Decimal("5"),
        customer_name="Txn User",
        customer_address="Txn Address",
        city="Txn City",
        postcode="54321",
        phone="0987654321",
        customer_email="txn@example.com"
    )
    txn = Transaction.objects.create(order=order, user=user, payment_method="Esewa", amount=Decimal("55"), status="Pending")
    assert "Txn" in str(txn)

@pytest.mark.django_db
def test_categorydeal_validation():
    import uuid
    unique_name = f"DealCat-{uuid.uuid4()}"
    cat = Category.objects.create(name=unique_name)
    deal = CategoryDeal(category=cat, end_date=timezone.now() + timezone.timedelta(days=1), is_active=True)
    deal.save()
    assert str(deal).startswith("Deal for")
    assert not deal.is_expired()
    assert isinstance(deal.time_remaining(), dict)
    # Test clean method for max 2 active deals
    deal2 = CategoryDeal(category=cat, end_date=timezone.now() + timezone.timedelta(days=2), is_active=True)
    deal2.save()
    deal3 = CategoryDeal(category=cat, end_date=timezone.now() + timezone.timedelta(days=3), is_active=True)
    with pytest.raises(ValidationError):
        deal3.full_clean()
