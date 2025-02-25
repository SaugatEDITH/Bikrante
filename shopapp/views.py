from decimal import Decimal
from django.contrib import messages
from django.db.models import Case, When, IntegerField
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
import re, random,os,requests 
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from .models import Category, Product,CartItem,Review,Order,OrderItem,Transaction
from django.urls import reverse
##! for create custom highend search querys
from django.db.models import Q
##! to seperate large data set to smaller managable pages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.middleware.csrf import get_token  # Add this import at the top
from django.db import transaction
##! for shipping price calculation
from .shipping_calculate import Shipping_Price
# esewa
import uuid
import requests as req
import hmac
import hashlib
import base64
import json
from decimal import Decimal
from django.http import HttpResponseNotFound
# All the function call returning the objects are at models
##! lodind key from .env file
from dotenv import load_dotenv
load_dotenv()
CLOUDFLARE_SECRET_KEY = os.getenv("CLOUDFLARE_TURNSTILE_SECRET")

##! home page view
def home(request):
    colors=['light-pink','light-orange','light-green','light-blue','light-red', 'light-purple', 'light-yellow', 'light-cyan']
    products=list(Product.objects.all())
    for product in products:
        if product.is_hot:
            product.class_color=random.choice(colors)
        else:
            product.class_color=None
    hot_products=[product for product in products if product.is_hot]
    normal_products=[product for product in products if not product.is_hot]
    categories = Category.objects.all()
    context = {
        'is_home':True, ##! yadi home ma card xa vani filter button natra total item no dekhauxa
        'categories':categories[::-1],
        'normal_products':normal_products[::-1],
        'hot_products':hot_products[::-1] ,
        'trending_products': Product.get_trending_products(),
        'new_arrivals': Product.get_new_arrivals(),
        'top_sellings': Product.get_top_selling(),
        'popular_products': Product.get_popular_products(),
    }
    return render(request, 'shopapp/index.html', context)

def shop(request):
    products = Product.objects.all()
    context = {
        'is_home': False,
        'products': products,
    }
    return render(request, 'shopapp/shop.html', context)




##! OLD search
# def search(request):
#     search_text = request.GET.get("search_text", "").strip()
#     page_num = int(request.GET.get('page', 1))
    
#     context = {
#         'is_home': False,
#         'search_text': search_text,
#         'current_page': page_num,
#     }
    
#     if search_text:
#         try:
#             # Split search terms
#             terms = search_text.lower().split()
#             # Start with all products
#             products = Product.objects.all()
            
#             # Apply each search term
#             for term in terms:
#                 products = products.filter(
#                     Q(name__icontains=term) |
#                     Q(description__icontains=term) |
#                     Q(category__name__icontains=term) |
#                     Q(brand_name__icontains=term) |
#                     Q(tags__icontains=term)
#                 )
            
#             # Pagination
#             paginator = Paginator(products, 12)
#             try:
#                 products = paginator.page(page_num)
#             except:
#                 products = paginator.page(1)
            
#             context.update({
#                 'products': products,
#                 'total_results': paginator.count,
#                 'has_results': True
#             })
            
#         except Exception as e:
#             print(f"Search error: {e}")
#             context.update({
#                 'products': [],
#                 'has_results': False,
#                 'error': str(e)
#             })
#     else:
#         # Show all products when no search
#         products = Product.objects.all().order_by('-created_at')
#         paginator = Paginator(products, 12)
#         try:
#             products = paginator.page(page_num)
#             context.update({
#                 'products': products,
#                 'total_results': paginator.count,
#                 'has_results': True
#             })
#         except:
#             context.update({
#                 'products': [],
#                 'has_results': False
#             })
    
#     if request.htmx:
#         return render(request, 'shopapp/includes/_search_results.html', context)
#     return render(request, 'shopapp/shop.html', context)


## ! God level search
def search(request):
    """
    The `search` function in Python handles searching for products based on user input and pagination,
    displaying results accordingly.
    
    :param request: The `search` function you provided is a view function in Django that handles
    searching for products based on the search text provided in the request. Here's a breakdown of the
    function:
    :return: The `search` function returns a rendered template based on the request type. If the request
    is made using HTMX (a library that allows for creating dynamic web pages using JavaScript), it
    returns the search results template (`shopapp/includes/_search_results.html`) with the context
    containing the search results data. If the request is not made using HTMX, it returns the main shop
    template (`shopapp/shop
    """
    search_text = request.GET.get("search_text", "").strip()
    page_num = int(request.GET.get('page', 1))

    context = {
        'is_home': False,
        'search_text': search_text,
        'current_page': page_num,
    }

    if search_text:
        try:
            # Split the search text into individual terms
            terms = search_text.lower().split()

            # Initialize the query for the OR logic (search any term in any relevant field)
            query = Q()

            # Create a query that matches any term in the name, description, category, etc.
            for term in terms:
                term_query = (
                    Q(name__icontains=term) |
                    Q(description__icontains=term) |
                    Q(category__name__icontains=term) |
                    Q(brand_name__icontains=term) |
                    Q(tags__icontains=term)
                )
                query |= term_query  # Use OR for combining terms (either term can match)

            # Apply the query to filter products
            products = Product.objects.filter(query)

            # Pagination
            paginator = Paginator(products, 12)
            products = paginator.get_page(page_num)

            context.update({
                'products': products,
                'total_results': paginator.count,
                'has_results': True
            })

        except Exception as e:
            print(f"Search error: {e}")
            context.update({
                'products': [],
                'has_results': False,
                'error': str(e)
            })
    else:
        # Show all products when no search text is provided
        products = Product.objects.all().order_by('-created_at')
        paginator = Paginator(products, 12)
        products = paginator.get_page(page_num)

        context.update({
            'products': products,
            'total_results': paginator.count,
            'has_results': True
        })

    if request.htmx:
        return render(request, 'shopapp/includes/_search_results.html', context)
    return render(request, 'shopapp/shop.html', context)



def calculate_page_range(paginator, current_page):
    """Calculate the range of pages to display"""
    if paginator.num_pages <= 7:
        return range(1, paginator.num_pages + 1)
    
    if current_page <= 4:
        return range(1, 8)
    
    if current_page >= paginator.num_pages - 3:
        return range(paginator.num_pages - 6, paginator.num_pages + 1)
    
    return range(current_page - 3, current_page + 4)
##! cloud flair captcha
def verify_turnstile(token):
    secret_key = CLOUDFLARE_SECRET_KEY
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {"secret": secret_key, "response": token}

    response = requests.post(url, data=data)
    return response.json()

##! Custom made Login page view
def login(request):
    context = {
        'is_login': True,
        'is_register': False,
        'message': []
    }
    if request.method == 'POST':
        token = request.POST.get("cf-turnstile-response")
        verification = verify_turnstile(token)
        if verification.get("success"):
            email = request.POST.get('email')
            password = request.POST.get('password')
            try:
                user = User.objects.get(email=email)
                user = authenticate(username=user.username, password=password)
                if user is not None:
                    auth_login(request, user)
                    return redirect('home')
                else:
                    context['message'].append("Invalid credentials")
            except User.DoesNotExist:
                context['message'].append("No account found with this email")
            return JsonResponse({"message": "Form submitted successfully!"})
        else:
            return JsonResponse({"error": "CAPTCHA failed!"}, status=400)
    return render(request, 'shopapp/login-register.html', context)

##! Custome made signup page view
def signup(request):
    context = {
        'is_login': False,
        'is_register': True,
        'message': []
    }
    if request.method == 'POST':
        token = request.POST.get("cf-turnstile-response")
        verification = verify_turnstile(token)
        if verification.get("success"):
          # Debug print
            username = request.POST.get('username')
            email = request.POST.get('email')
        # Email validation
            if not re.fullmatch(r'^[A-Za-z][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
                context['message'].append("Invalid email format. Email cannot start with a number.")
                return render(request, 'shopapp/login-register.html', context)
            password = request.POST.get('password')
            confirm_password = request.POST.get('cpassword')
            print(f"Form data: {username}, {email}")  # Debug print
        # Password validation
            if not re.fullmatch(r'(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}', password):
                context['message'].append("Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.")
                return render(request, 'shopapp/login-register.html', context)
            if password != confirm_password:
                context['message'].append("Passwords do not match.")
                return render(request, 'shopapp/login-register.html', context)
            if User.objects.filter(username=username).exists():
                context['message'].append("Username already taken!")
                return render(request, 'shopapp/login-register.html', context)
            if User.objects.filter(email=email).exists():
                context['message'].append("Email already in use!")
                return render(request, 'shopapp/login-register.html', context)
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            auth_login(request, user)
            return redirect('home')
        else:
            return JsonResponse({"error": "CAPTCHA failed!"}, status=400)
    return render(request, 'shopapp/login-register.html', context)

@login_required
def user_logout(request):
    logout(request)
    return redirect('home')

def contact(request):
    breadcrumb_items = [
        {'title': 'Home', 'url': reverse('home')},
        {'title': 'Contact', 'url': None}  # Current page doesn't need URL
    ]
    return render(request, 'shopapp/contact.html', {'breadcrumb_items': breadcrumb_items})

@login_required(login_url='login')
def user_dashboard(request):
    orders=Order.objects.filter(user=request.user)[::-1][:10]
    context={
        'message':[],
        'orders':orders,
    }
    if request.method=="POST":
        #handaling username Update
        if 'update_username' in request.POST:
            new_username=request.POST.get('username')
            if User.objects.filter(username=new_username).exists():
                context['message'].append("This username is already taken")
                return redirect('user-dashboard#update-profile')
            else:
                request.user.username=new_username
                request.user.save()
                context['message'].append("Your username has been sucessfully updated.")
                return redirect('user-dashboard')
            
        elif 'change_password' in request.POST:
            current_password=request.POST.get("current_password")
            new_password=request.POST.get("new_password")
            confirm_password=request.POST.get("confirm_password")
            
            user=authenticate(request.user.username,password=current_password)
            if user:
                if new_password==confirm_password:
                    if not re.fullmatch(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', new_password):
                         context['message'].append("Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.")
                         return redirect("user-dashboard#change-password")
                    user.set_password(new_password)
                    user.save()
                    auth_login(request,user) #re-log user after password change
                    context['message'].append("Your password has been sucessfully updated")
                    return redirect("user-dashboard")
                else:
                    context['message'].append("New password and confirm password don't match.")
            else:
                context['message'].append("Current password is incorrect.")
    return render(request,'shopapp/user-dashboard.html',context)

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.all()  # Get all products in this category
    context={
        'category':category,
        'products':products
             }
    return render(request, 'shopapp/shop.html',context)

def product_detail(request, slug):

    product = get_object_or_404(Product, slug=slug)
    product.increment_views()  # Record the view
    user= request.user if request.user.is_authenticated else None
    user_reviews=Review.objects.filter(product=product,user=user).first()
    reviews=Review.objects.filter(product=product).exclude(user=user)
    ## Best for large dataset slower for smaller
    # reviews = Review.objects.filter(product=product).annotate(
    #     is_current_user=Case(
    #         When(user=user, then=0),  # Give priority to current user's review
    #         default=1,
    #         output_field=IntegerField()
    #     )
    # ).order_by('is_current_user', '-created_at')
    
    # Generate breadcrumb data
    if user_reviews:
        reviews = [user_reviews] +list(reviews) 
    # Generate star icons safely
    for review in reviews:
    # <i class='fi fi-rs-star'></i>
        review.star_icons = ["⭐" for _ in range(0,review.rating or 0)]
  
    breadcrumb_items = [
        {'title': 'Home', 'url': reverse('home')},
        {'title': product.category.name, 'url': product.category.get_absolute_url()},
        {'title': product.name, 'url': None}  # Current page doesn't need URL
    ]
    
    context = {
        'product': product,
        'cross_sell_products': product.get_cross_sell_products(),
        'upsell_products': product.get_upsell_products(),
        'breadcrumb_items': breadcrumb_items,
        'reviews':reviews,
        'reviews_count':len(reviews),
    }
    if request.htmx:
        if 'reviews' in request.POST:
            print("hello world")
            print(request.POST.get('review'))
            print(request.POST.get('rating'))
            pass
        return render(request, "shopapp/partials/_partial-details.html", {"product": product})
    return render(request, 'shopapp/details.html', context)
# Review count update
def product_review_count(request, slug):
    """HTMX view to return updated review count."""
    product = get_object_or_404(Product, slug=slug)
    review_count = Review.objects.filter(product=product).count()
    return HttpResponse(review_count)

@login_required(login_url='login')
def wishlist(request):
    liked_products = Product.objects.filter(likes=request.user)
    if request.htmx:
        if not request.user.is_authenticated:
            return redirect('login')
        liked_products.likes.remove(request.user)
        liked_products.save()
        return render(request, 'shopapp/wishlist.html', {
            'liked_products': liked_products
            })
    return render(request, 'shopapp/wishlist.html',{'liked_products':liked_products})

def add_remove_wishlist(request, slug):
    if not request.user.is_authenticated:
        if request.htmx:
            response = JsonResponse({"redirect": True})
            response["HX-Redirect"] = "/login/"  # Redirect to login
            return response
        return redirect('login')  # Normal redirect for non-HTMX requests
    if request.method == "POST":
        product = get_object_or_404(Product, slug=slug)
        was_liked = product.likes.filter(id=request.user.id).exists()
        
        if was_liked:
            product.likes.remove(request.user)
            is_liked = False
        else:
            product.likes.add(request.user)
            is_liked = True
            
        count = request.user.liked_products.count()
        
        return JsonResponse({
            'success': True,
            'is_liked': is_liked,
            'wishlist_count': count,
            'wishlist_action':"wishlist_update",
            'product_slug': slug
        })
    ##! To delete from the wishlist
    if request.method == "DELETE":
        product = get_object_or_404(Product, slug=slug)
        product.likes.remove(request.user)
        count = request.user.liked_products.count()
        
        # Update both the wishlist count and remove the item
        return JsonResponse({
            'success': True,
            'wishlist_count': count,
            'wishlist_action':"wishlist_update",
            'product_slug': slug
        })
    
    return JsonResponse({'success': False}, status=400)
##! for calculating shipping price
def shipping_price_view(request):
    province = request.GET.get("province")
    district = request.GET.get("district")
    city = request.GET.get("city")

    if not all([province, district, city]):
        return JsonResponse({"error": "Missing parameters"}, status=400)

    cost = Shipping_Price(province, district, city)

    if cost is None:
        return JsonResponse({"error": "Invalid location"}, status=400)

    return JsonResponse({"shipping_cost": cost})

@login_required(login_url='login')
def cart(request):
    if request.method=="POST":
        pass
    cart_items=CartItem.objects.filter(user=request.user)
    overall_subtotal = sum([
        (setattr(cart_item, 'subtotal', cart_item.product.price_after_discount * cart_item.quantity) or cart_item.subtotal)
        if cart_item.product.price_after_discount else
        (setattr(cart_item, 'subtotal', cart_item.product.price * cart_item.quantity) or cart_item.subtotal)
        for cart_item in cart_items
    ])

    shipping_price=150 if overall_subtotal>0 else 0
    total_price=overall_subtotal+shipping_price
    context={
        'cart_items':cart_items,
        'subtotal':overall_subtotal,
        'shipping_price':shipping_price,
        'total_price':total_price,
        }
    
    return render(request,'shopapp/cart.html',context=context)
   
    



def add_remove_cart(request, slug):
    if not request.user.is_authenticated:
        if request.htmx:
            response = JsonResponse({"redirect": True})
            response["HX-Redirect"] = "/login/"  # Redirect to login
            return response
        return redirect('login')  # Normal redirect for non-HTMX requests

    product = get_object_or_404(Product, slug=slug)
    if request.method == "POST":
        quantity = int(request.POST.get(f"quantity-{slug}", 1))
        cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
        
        if created:
            cart_item.quantity = quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        # Calculate the item subtotal
        item_subtotal = cart_item.quantity * product.price_after_discount

        # Recalculate the total cart subtotal and total price
        cart_items = CartItem.objects.filter(user=request.user)
        cart_subtotal = sum([item.quantity * item.product.price_after_discount for item in cart_items])
        shipping_price = 10  # Add your shipping price logic here
        total_price = cart_subtotal + shipping_price

        # Return JSON response with item-specific and cart totals
        count = request.user.cart_items.count()

        return JsonResponse({
            'success': True,
            'action': 'updated',
            'cart_count': count,
            'product_slug': slug,
            'item_quantity': cart_item.quantity,
            'item_subtotal': f"{item_subtotal:.2f}",  # Format as needed
            'cart_subtotal': f"{cart_subtotal:.2f}",  # Total for all items in the cart
            'shipping_price': shipping_price,
            'total_price': f"{total_price:.2f}",  # Total including shipping
        })

    if request.method == "DELETE":
        cart_item = CartItem.objects.filter(user=request.user, product=product).first()
        if cart_item:
            cart_item.delete()

        cart_items = CartItem.objects.filter(user=request.user)
        cart_subtotal = sum([item.quantity * item.product.price_after_discount for item in cart_items])
        shipping_price = 10  # Add your shipping price logic here
        total_price = cart_subtotal + shipping_price
        count = request.user.cart_items.count()

        return JsonResponse({
            'success': True,
            'action': 'removed',
            'cart_count': count,
            'product_slug': slug,
            'cart_subtotal': f"{cart_subtotal:.2f}",
            'shipping_price': shipping_price,
            'total_price': f"{total_price:.2f}",
        })

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required(login_url='login')
def checkout(request):
    
    
    # Generate breadcrumb data
    cart_items = CartItem.objects.filter(user=request.user)
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.error(request, "Your cart is empty. Please add items to your cart before proceeding.")
        return redirect('shop')  # Redirect to the shop page or any other appropriate page
    
    # Breadcrumb context
    breadcrumb_items = [
        {'title': 'Shop', 'url': reverse('shop')},
        {'title': 'Checkout', 'url': None}  # Current page doesn't need URL
    ]
    
    # Calculate prices
    cart_subtotal = sum(Decimal(item.total_price()) for item in cart_items)
    shipping_price = 150 if cart_subtotal > 0 else 0  # Add logic for dynamic shipping
    total_price = cart_subtotal + shipping_price
    
    # Debugging output (optional)
    print(f"Cart Subtotal: {cart_subtotal}, Shipping Price: {shipping_price}, Total Price: {total_price}")
    
    # Render checkout page with the calculated data
   
    
    if request.method == "POST":
        name=request.POST.get("name")
        address=request.POST.get("address")
        city=request.POST.get("city")
        postcode=request.POST.get("postcode")
        phone=request.POST.get("phone")
        email=request.POST.get("email")
        payment_method=request.POST.get("payment_method")
        order_note=request.POST.get("order_note")
        print(name,address,city,postcode,phone,email,payment_method,order_note)
        
        # Create order and order items only if form is submitted (POST request)
        try:
            with transaction.atomic():  # Ensure all database operations happen together
                # Create the Order
                order = Order.objects.create(user=request.user,total_price=total_price,shipping_price=100,customer_name=name,customer_address=address,city=city,postcode=postcode,phone=phone,customer_email=email,order_note=order_note,)

                # Create OrderItems from CartItems
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.total_price(),  # Price at the time of purchase
                    )

                # Clear the cart after order is placed
                cart_items.delete()
                messages.success(request, "Order placed successfully!")
                # return redirect("order_success", order_id=order.id)
                if payment_method=="Esewa":
                    return redirect("esewa_checkout", order_id=order.id)
                if payment_method=="Khalti":
                    return redirect("khalti_checkout", order_id=order.id)
                if payment_method=="Paypal":
                    return redirect("paypal_checkout", order_id=order.id)
                if payment_method=="COD":
                    messages.success(request, "Your Cash on Delivery order has been placed.")
                    return redirect("user-dashboard",order_id=order.id)
            return redirect('shop')
        except Exception as e:
            # Log or print the error for debugging
            print(f"Error placing order: {e}")
            messages.error(request, "There was an issue processing your order. Please try again.")
            return redirect('shop')
    context = {
        'breadcrumb_items': breadcrumb_items,
        'cart_items': cart_items,
        'cart_subtotal': cart_subtotal,
        'shipping_price': shipping_price,
        'total_price': total_price,
    }
    # Return the initial checkout page if GET request
    return render(request, 'shopapp/checkout.html', context)
# For Payment Gateways
# for esewa
def esewa(request, order_id):
    order =get_object_or_404(Order,id=order_id)
    try:
        amount=Decimal( request.POST.get("amount",order.total_price) )
    except:
        messages.error(request,"Invalid amount format.")
        return redirect("checkout",order_id=order_id)
    def genSha256(key, message):
        key = key.encode('utf-8')
        message = message.encode('utf-8')
        hmac_sha256 = hmac.new(key, message, hashlib.sha256)
        digest = hmac_sha256.digest()
        # Convert the digest to a Base64-encoded string
        signature = base64.b64encode(digest).decode('utf-8')
        return signature
        
    total_amount = amount
    secret_key = "8gBm/:&EnhH.1/q"  #form esewa Docs
    uid= str(uuid.uuid4())
    data_to_sign = f"total_amount={total_amount},transaction_uuid={uid},product_code=EPAYTEST" #form esewa Docs and v2 requirements
    result = genSha256(secret_key, data_to_sign)
        
    context = {
            "order": order,
            'total_amount': total_amount,
            'uid': uid,
            'signature': result,
            "success_url": request.build_absolute_uri(f"/esewa-payment-success/{order.id}/"),
            # 'delivery_charge':
        }
    return render(request, "shopapp/foresewa.html", context)
    



def esewa_payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "GET":
        try:
            # Get the encoded data from URL
            encoded_data = request.GET.get('data')
            if not encoded_data:
                messages.error(request, "No payment data received")
                return redirect("checkout")
            
            # Add padding if needed
            padding = 4 - (len(encoded_data) % 4)
            if padding != 4:
                encoded_data += '=' * padding
                
            # Decode the base64 data
            try:
                decoded_data = base64.b64decode(encoded_data)
                payment_data = json.loads(decoded_data.decode('utf-8'))
            except Exception as e:
                print(f"Decoding error: {e}")
                messages.error(request, "Invalid payment data format")
                return redirect("checkout")
            
            # Verify payment status
            if payment_data.get('status') == 'COMPLETE':
                # Create transaction record
                Transaction.objects.create(
                    order=order,
                    user=request.user,
                    payment_method='Esewa',
                    amount=Decimal(str(payment_data.get('total_amount', '0').replace(',', ''))),
                    esewa_transaction_id=payment_data.get('transaction_uuid'),
                    status='Success'
                )
                
                # Update order status
                order.payment = True
                order.status = 'Completed'
                order.save()
                
                messages.success(request, "Payment successful! Your order has been confirmed.")
                return redirect("user-dashboard")
            else:
                messages.error(request, "Payment was not completed successfully.")
                return redirect("checkout")
                
        except Exception as e:
            print(f"Payment processing error: {e}")
            messages.error(request, "There was an error processing your payment.")
            return redirect("checkout")
            
    return redirect("user-dashboard")

def khalti(request):
    pass
def paypal(request):
    pass