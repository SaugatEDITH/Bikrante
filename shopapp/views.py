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
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed
from .models import Category, CategoryDeal, Product,CartItem,Review,Order,OrderItem,Transaction, UserProfile,Contact, NewsletterSubscriber
from django.urls import reverse
##! for create custom highend search querys
from django.db.models import Q
##! to seperate large data set to smaller managable pages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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
from django.db.models import Avg
# All the function call returning the objects are at models
from django.conf import settings
from paypal.standard.forms import PayPalPaymentsForm
from django.urls import reverse
from django.template.loader import render_to_string  # Add this import at the top
from django.views.decorators.http import require_POST
import logging
logger = logging.getLogger(__name__)
# s
from django.http import HttpResponse
from io import BytesIO
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
# from django.utils.crypto import get_random_string
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import make_password
# from django.conf.urls import handler404
##! lodind gangajal
import gangajal
##! lodind key from .env file
from dotenv import load_dotenv
load_dotenv()
CLOUDFLARE_SECRET_KEY = os.getenv("CLOUDFLARE_TURNSTILE_SECRET")
DEEPSEEK_R1_SECRET = os.getenv("DEEPSEEK_R1_SECRET")

from .models import UserActivityEvent
from .recommender import recommend_for_request, fallback_recommendations


def _get_or_create_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def _get_anon_id(request):
    return request.COOKIES.get("anon_id", "")


def _get_fingerprint(request):
    return request.COOKIES.get("fp", "")


def _merge_activity_to_user(request, user):
    anon_id = _get_anon_id(request)
    fp = _get_fingerprint(request)
    session_key = request.session.session_key or ""

    q = UserActivityEvent.objects.filter(user__isnull=True)
    filters = Q()
    if anon_id:
        filters |= Q(anon_id=anon_id)
    if fp:
        filters |= Q(fingerprint=fp)
    if session_key:
        filters |= Q(session_key=session_key)

    if filters:
        q = q.filter(filters)
        q.update(user=user)


##! home page view
def home(request):
    colors=['light-pink','light-orange','light-green','light-blue','light-red', 'light-purple', 'light-yellow', 'light-cyan']
    # products=list(Product.objects.all())
    products=Product.get_products()
    
    for product in products:
        if product.is_hot:
            product.class_color=random.choice(colors)
        else:
            product.class_color=None
    hot_products=[product for product in products if product.is_hot]
    normal_products=[product for product in products if not product.is_hot]
    categories = Category.objects.all()
    
    # Get all active deals
    active_deals = CategoryDeal.objects.filter(
        is_active=True, 
        end_date__gt=timezone.now()
    ).select_related('category')[:2]  # Limit to 2 deals
    
    context = {
        'is_home': True,
        'categories': categories[::-1],
        'normal_products': normal_products[::-1],
        'hot_products': hot_products[::-1],
        'trending_products': Product.get_trending_products(),
        'new_arrivals': Product.get_new_arrivals(),
        'top_sellings': Product.get_top_selling(),
        'popular_products': Product.get_popular_products(),
        'active_deals': active_deals,
    }
    return render(request, 'shopapp/index.html', context)

def shop(request):
    page_num = int(request.GET.get('page', 1))

    # ensure we have a stable identity even for anonymous users
    _get_or_create_session_key(request)
    anon_id = _get_anon_id(request)
    fp = _get_fingerprint(request)

    # Pull products and apply recommendation ordering
    base_products = list(Product.objects.select_related("category").annotate(avg_rating_cache=Avg('reviews__rating')).all())

    reco = recommend_for_request(user=request.user, anon_id=anon_id, fingerprint=fp, limit=200)
    if not reco.product_ids:
        reco = fallback_recommendations(limit=200)

    reco_rank = {pid: idx for idx, pid in enumerate(reco.product_ids)}

    def _sort_key(p):
        # 0 = in stock, 1 = out of stock
        stock_group = 0 if (getattr(p, "stock", 0) and p.stock > 0) else 1
        # recommended products come first; then by latest id
        rank = reco_rank.get(p.id, 10**9)
        return (stock_group, rank, -p.id)

    base_products.sort(key=_sort_key)
    products_qs = Product.add_star_ratings(base_products)
    
    paginator = Paginator(products_qs, 12)
    try:
        products_page = paginator.page(page_num)
    except PageNotAnInteger:
        products_page = paginator.page(1)
        page_num = 1
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
        page_num = paginator.num_pages

    # Get current compare items from session
    compare_items = request.session.get('compare_items', [])

    context = {
        'is_home': False,
        'products': products_page,
        'products_page': products_page,
        'compare_items': compare_items,
        'current_page': page_num,
        'page_range': calculate_page_range(paginator, page_num),
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'Shop', 'url': None},
        ],
    }

    if request.htmx:
        return render(request, 'shopapp/includes/_shop_results.html', context)

    response = render(request, 'shopapp/shop.html', context)
    # If anon_id isn't set yet, JS will set it; still keep session stable.
    return response


@require_POST
def activity_track(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

    events = payload.get("events") or []
    if not isinstance(events, list) or not events:
        return JsonResponse({"success": True, "ingested": 0})

    anon_id = payload.get("anon_id") or _get_anon_id(request)
    fp = payload.get("fingerprint") or _get_fingerprint(request)
    page = payload.get("page") or "shop"
    session_key = _get_or_create_session_key(request)

    user = request.user if request.user.is_authenticated else None

    to_create = []
    for e in events:
        try:
            product_id = int(e.get("product_id"))
        except Exception:
            continue

        event_type = (e.get("event_type") or "").strip()
        duration_ms = e.get("duration_ms")
        if duration_ms is not None:
            try:
                duration_ms = int(duration_ms)
            except Exception:
                duration_ms = None

        meta = e.get("meta")
        if not isinstance(meta, dict):
            meta = {}

        if event_type not in {"impression", "dwell", "hover", "click", "quick_view", "add_to_cart", "wishlist"}:
            continue

        to_create.append(
            UserActivityEvent(
                user=user,
                anon_id=str(anon_id or ""),
                session_key=str(session_key or ""),
                fingerprint=str(fp or ""),
                product_id=product_id,
                event_type=event_type,
                duration_ms=duration_ms,
                page=page,
                metadata=meta,
            )
        )

    if not to_create:
        return JsonResponse({"success": True, "ingested": 0})

    UserActivityEvent.objects.bulk_create(to_create, batch_size=500)
    resp = JsonResponse({"success": True, "ingested": len(to_create)})
    if anon_id:
        resp.set_cookie("anon_id", str(anon_id), max_age=60 * 60 * 24 * 365, samesite="Lax")
    if fp:
        resp.set_cookie("fp", str(fp), max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


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
    search_text = request.GET.get("search_text", "").strip()
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    sort = request.GET.get("sort")  # Match the form name from the filter dropdown
    page_num = int(request.GET.get('page', 1))

    context = {
        'is_home': False,
        'search_text': search_text,
        'current_page': page_num,
        'min_price': min_price,
        'max_price': max_price,
        'sort': sort,
    }

    # Base query - either search results or all products
    if search_text:
        terms = search_text.lower().split()
        query = Q()
        for term in terms:
            term_query = (
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(category__name__icontains=term) |
                Q(brand_name__icontains=term) |
                Q(tags__icontains=term)
            )
            query |= term_query
        products = Product.objects.filter(query)
    else:
        products = Product.objects.all()

    # Apply filters
    if min_price:
        products = products.filter(price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(price__lte=Decimal(max_price))
    if sort:
        if sort == "price_asc":
            products = products.order_by('price')
        elif sort == "price_desc":
            products = products.order_by('-price')
    else:
        # Ensure default ordering to avoid UnorderedObjectListWarning
        products = products.order_by('id')

    # Pagination
    paginator = Paginator(products, 12)
    try:
        products = paginator.page(page_num)
        context.update({
            'products': products,
            'total_results': paginator.count,
            'has_results': True,
            'page_range': calculate_page_range(paginator, page_num),
        })
    except PageNotAnInteger:
        products = paginator.page(1)
        context.update({
            'products': products,
            'total_results': paginator.count,
            'has_results': True,
            'page_range': calculate_page_range(paginator, 1),
        })
    except EmptyPage:
        # fallback if beyond page range
        products = paginator.page(paginator.num_pages)
        context.update({
             'products': products,
             'total_results': paginator.count,
             'has_results': True,
             'page_range': calculate_page_range(paginator, paginator.num_pages),
        })
    except Exception as e:
        print(f"Pagination error: {e}")
        context.update({
            'products': [],
            'has_results': False,
            'error': str(e),
        })

    # Render HTMX partial or full page
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
def verify_turnstile(token, remoteip=None):
    secret_key = CLOUDFLARE_SECRET_KEY
    if not secret_key or not token:
        return {"success": False}

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {"secret": secret_key, "response": token}
    if remoteip:
        data["remoteip"] = remoteip

    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception:
        logger.exception("Turnstile verification request failed")
        return {"success": False}

##! Custom made Login page view
def login(request):

    context = {
        'is_login': True,
        'is_register': False,
        'message': [],
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'Login', 'url': None},
        ],
    }
    
    if request.method == 'POST':
        token = request.POST.get("cf-turnstile-response") or request.POST.get("cf_turnstile_response")
        verification = verify_turnstile(token, remoteip=request.META.get('REMOTE_ADDR'))
        if verification.get("success"):
            email = request.POST.get('email')
            password = request.POST.get('password')
            try:
                user = User.objects.get(email=email)

                user = authenticate(username=user.username, password=password)
                if user is not None:
                    auth_login(request, user)
                    _merge_activity_to_user(request, user)
                    return redirect('home')
                else:
                    messages.error(request,"Invalid credentials")
            except User.DoesNotExist:
                messages.error(request,"No account found with this email")
        else:
            if verification.get("error-codes"):
                logger.warning("Turnstile login failed: %s", verification.get("error-codes"))
            messages.error(request, "CAPTCHA verification failed. Please try again.")
    return render(request, 'shopapp/login-register.html', context)

##! Custome made signup page view
def signup(request):

    context = {
        'is_login': False,
        'is_register': True,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'Register', 'url': None},
        ],
    }
    
    if request.method == 'POST':
        token = request.POST.get("cf-turnstile-response") or request.POST.get("cf_turnstile_response")
        verification = verify_turnstile(token, remoteip=request.META.get('REMOTE_ADDR'))
        if verification.get("success"):
            username = request.POST.get('username')
            email = request.POST.get('email')
        # Email validation
            if not re.fullmatch(r'^[A-Za-z][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
                messages.error(request,"Invalid email format. Email cannot start with a number.")
                return render(request, 'shopapp/login-register.html', context)

            password = request.POST.get('password')
            confirm_password = request.POST.get('cpassword')

        # Password validation
            if not re.fullmatch(r'(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}', password):
                messages.error(request,"Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character.")
                return render(request, 'shopapp/login-register.html', context)
            if password != confirm_password:
                messages.error(request,"Passwords do not match.")
                return render(request, 'shopapp/login-register.html', context)
            if User.objects.filter(username=username).exists():
                messages.error(request,"Username already taken!")
                return render(request, 'shopapp/login-register.html', context)
            if User.objects.filter(email=email).exists():
                messages.error(request,"Email already in use!")
                return render(request, 'shopapp/login-register.html', context)
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            auth_login(request, user)
            return redirect('profile-onboarding')
        else:
            if verification.get("error-codes"):
                logger.warning("Turnstile signup failed: %s", verification.get("error-codes"))
            messages.error(request, "CAPTCHA verification failed. Please try again.")
    return render(request, 'shopapp/login-register.html', context)

@login_required
def user_logout(request):
    logout(request)
    return redirect('home')

def contact(request):
    breadcrumb_items = [
        {'title': 'Home', 'url': reverse('home')},
        {'title': 'Contact', 'url': None},
        # Current page doesn't need URL
    ]

    if request.method=="POST":
        token = request.POST.get("cf-turnstile-response")
        verification = verify_turnstile(token)
        if verification.get("success"):
            name=request.POST.get('name')
            email=request.POST.get('email')
            subject=request.POST.get('subject')
            message=request.POST.get('message')
            if not name or len(name) < 3: 
                messages.error(request,"Name must be at least 3 characters long.") 
            if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email): 
                messages.error(request,"Enter a valid email address.") 
            if not subject or len(subject) < 5: 
                messages.error(request,"Subject must be at least 5 characters long.") 
            if not message or len(message) < 10: 
                messages.error(request,"Message must be at least 10 characters long.") 
            else:
                tosave=Contact(name=name,email=email,subject=subject,message=message)
                tosave.save()
                messages.success(request,'form submitted sucessfully')
        else:
            messages.error(request,"captcha failed")
    return render(request, 'shopapp/contact.html', {'breadcrumb_items': breadcrumb_items})

@login_required(login_url='login')
def user_dashboard(request):
    orders = Order.objects.filter(user=request.user)[::-1][:10]
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    address_parts = profile.address.split(',') if profile.address else []
    city = address_parts[-1].strip() if address_parts else "Unknown"

    liked_products = (
        Product.objects.filter(likes=request.user)
        .select_related("category")
        .annotate(avg_rating_cache=Avg('reviews__rating'))
    )
    user_reviews = (
        Review.objects.filter(user=request.user)
        .select_related("product", "product__category")
        .order_by("-updated_at")
    )

    # Sanitize review text before rendering
    for r in user_reviews:
        if r.review_text:
            r.review_text = gangajal.validate(r.review_text, 1)

    context = {
        'message': [],
        'orders': orders,
        'profile': profile,
        'city': city,  # Pass city separately
        'liked_products': liked_products,
        'user_reviews': user_reviews,
        "onboarding": False,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'My Account', 'url': None},
        ],
    }
    
    if request.method == "POST":
        if 'update_profile' in request.POST:
            # Handle username update
            new_username = request.POST.get('username')
            if new_username and new_username != request.user.username:
                if User.objects.filter(username=new_username).exists():
                    context['message'].append("This username is already taken")
                else:
                    request.user.username = new_username
                    request.user.save()
                    context['message'].append("Username updated successfully")
            
            # Handle profile updates
            new_address = request.POST.get('address')
            new_phone = request.POST.get('phone_number')
            new_image = request.FILES.get('profile_image')
            
            if new_address:
                profile.address = new_address
            if new_phone:
                mobile_regex = r"^(97|98)\d{7,8}$"
                landline_regex = r"^(01|04|05|06|07)\d{6,7}$"
                if not (re.match(mobile_regex, new_phone) or re.match(landline_regex, new_phone)):
                    context['message'].append("Enter a valid phone number.")
                    return JsonResponse({
                        "status": "error",
                        "message": "Enter a valid nepali phone number.",
                        "redirect": "/user-dashboard/"
                    })
                else:
                    profile.phone_number = new_phone
            if new_image:
                if not new_image.name.lower().endswith(('jpeg', 'png', 'jpg')):
                    context['message'].append("Only JPEG, PNG, and JPG image formats are allowed.")
                    return JsonResponse({
                "status": "error",
                "message": "Only JPEG, PNG, and JPG image formats are allowed.",
                "redirect": "/user-dashboard/"
            })
                else:
                    profile.profile_image = new_image
            
            profile.save()
            
            if any([new_address, new_phone, new_image]):
                context['message'].append("Profile updated successfully")
            return JsonResponse({
                "status": "success",
                "message": "Profile updated successfully.",
                "redirect": "/user-dashboard/"
            })
        elif 'change_password' in request.POST:
            current_password = request.POST.get("current_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")
            
            user = authenticate(username=request.user.username, password=current_password)
            if user:
                if new_password == confirm_password:
                    if not re.fullmatch(r'(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}', new_password):
                        return JsonResponse({
                            "status": "error",
                            "message": "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character."
                        })
                    user.set_password(new_password)
                    user.save()
                    auth_login(request, user)
                    return JsonResponse({
                        "status": "success",
                        "message": "Your password has been successfully updated.",
                        "redirect": "/user-dashboard/"
                    })
                else:
                    return JsonResponse({
                        "status": "error",
                        "message": "New password and confirm password don't match."
                    })
            else:
                return JsonResponse({
                    "status": "error",
                    "message": "Current password is incorrect."
                })
    return render(request, 'shopapp/user-dashboard.html', context)

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.select_related("category").annotate(avg_rating_cache=Avg('reviews__rating'))  # Get all products in this category
    products = Product.add_star_ratings(list(products))
    context={
        'category':category,
        'products':products,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': category.name, 'url': None},
        ],
    }
    return render(request, 'shopapp/shop.html',context)

def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug)
    product.increment_views()
    # Fetch related products using the improved method
    related_products = Product.get_related_products(product)

    def _ensure_review_user_profiles(review_list):
        """Bulk-create missing UserProfiles for review users to avoid template crashes."""
        user_ids = [r.user_id for r in review_list if getattr(r, "user_id", None)]
        if not user_ids:
            return
        existing_user_ids = set(
            UserProfile.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True)
        )
        missing_user_ids = [uid for uid in set(user_ids) if uid not in existing_user_ids]
        if missing_user_ids:
            UserProfile.objects.bulk_create([UserProfile(user_id=uid) for uid in missing_user_ids])

    def _sanitize_review_text(review_list):
        """Apply gangajal bad word validation to review text before rendering."""
        for r in review_list:
            if r.review_text:
                r.review_text = gangajal.validate(r.review_text, 1)
        return review_list

    # Handle review submission via HTMX
    if request.method == "POST" and 'review_submit' in request.POST:
        if not request.user.is_authenticated:
            return JsonResponse({
                "status": "error", 
                "message": "Please login to leave a review",
                "reload": True
            })
        
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text', '').strip()
        
        # Fix validation logic
        if not (rating and int(rating) >= 1 and len(review_text) >= 4):
            return JsonResponse({
                "status": "error",
                "message": "Rating and review required."
            })
        
        try:
            review, created = Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': rating,
                    'review_text': review_text,
                    'ip': request.META.get('REMOTE_ADDR')
                }
            )
            
            # Get updated reviews
            user_reviews = (
                Review.objects.select_related("user")
                .filter(product=product, user=request.user)
                .first()
            )
            reviews = list(
                Review.objects.select_related("user")
                .filter(product=product)
                .exclude(user=request.user)
            )
            if user_reviews:
                reviews = [user_reviews] + reviews

            for r in reviews:
                r.star_icons = ["⭐" for _ in range(0, r.rating or 0)]

            _ensure_review_user_profiles(reviews)
            _sanitize_review_text(reviews)

            context = {
                'product': product,
                'reviews': reviews,
                'reviews_count': len(reviews),
                'user_review': user_reviews,
            }
            
            response_html = render_to_string(
                'shopapp/partials/_reviews_section.html',
                context=context,
                request=request
            ).strip()

            return HttpResponse(response_html)
            
        except Exception as e:
            logger.exception("Review submit failed: %s", e)
            return JsonResponse({
                "status": "error",
                "message": "An error occurred while saving your review"
            })

    # Handle review delete via HTMX
    if request.method == "POST" and 'review_delete' in request.POST:
        if not request.user.is_authenticated:
            return JsonResponse({"status": "error", "message": "Login required"}, status=403)
        
        try:
            # Delete user's review for this product
            Review.objects.filter(product=product, user=request.user).delete()
            
            # Get updated reviews
            user_reviews = None
            reviews = list(
                Review.objects.select_related("user")
                .filter(product=product)
            )
            
            for r in reviews:
                r.star_icons = ["⭐" for _ in range(0, r.rating or 0)]

            _sanitize_review_text(reviews)

            context = {
                'product': product,
                'reviews': reviews,
                'reviews_count': len(reviews),
                'user_review': user_reviews,
            }
            
            response_html = render_to_string(
                'shopapp/partials/_reviews_section.html',
                context=context,
                request=request
            ).strip()

            return HttpResponse(response_html)
            
        except Exception as e:
            logger.exception("Review delete failed: %s", e)
            return JsonResponse({"status": "error", "message": "Could not delete review"}, status=500)

    # Rest of view logic for GET request
    user = request.user if request.user.is_authenticated else None
    user_reviews = (
        Review.objects.select_related("user")
        .filter(product=product, user=user)
        .first()
    )
    reviews = (
        Review.objects.select_related("user")
        .filter(product=product)
        .exclude(user=user)
    )
    if user_reviews:
        reviews = [user_reviews] + list(reviews)

    for review in reviews:
        review.star_icons = ["⭐" for _ in range(0, review.rating or 0)]

    _sanitize_review_text(reviews)

    context = {
        'product': product,
        'reviews': reviews,
        'reviews_count': len(reviews),
        'user_review': user_reviews,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': product.category.name, 'url': product.category.get_absolute_url()},
            {'title': product.name, 'url': None}
        ],
        'related_products': related_products,
    }

    if request.htmx:
        return render(request, "shopapp/partials/_partial-details.html", {"product": product})
    return render(request, 'shopapp/details.html', context)
def product_review_count(request, slug):
    """HTMX view to return updated review count."""
    product = get_object_or_404(Product, slug=slug)
    review_count = Review.objects.filter(product=product).count()
    return HttpResponse(review_count)

@login_required(login_url='login')
def wishlist(request):
    liked_products = Product.objects.filter(likes=request.user)
    breadcrumb_items = [
        {'title': 'Home', 'url': reverse('home')},
        {'title': 'Wishlist', 'url': None},
    ]
    if request.htmx:
        if not request.user.is_authenticated:
            return redirect('login')
        liked_products.likes.remove(request.user)
        liked_products.save()
        return render(request, 'shopapp/wishlist.html', {
            'liked_products': liked_products,
            'breadcrumb_items': breadcrumb_items,
            })
    return render(request, 'shopapp/wishlist.html',{'liked_products':liked_products, 'breadcrumb_items': breadcrumb_items})

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
        action="added" if is_liked else "removed"
        return JsonResponse({
            ##!for toster
            "status": "success",
            "message": f"The product has been {action}",
            ##!
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
            ##!for toster
            "status": "success",
            "message": f"The product has been removed",
            ##!
            'success': True,
            'wishlist_count': count,
            'wishlist_action':"wishlist_update",
            'product_slug': slug
        })
    
    return JsonResponse({'success': False}, status=400)

##! for calculating shipping price
@login_required(login_url='login')
def set_shipping_price_in_session(request, province=None, district=None, city=None):
    """
    Set or update the shipping price in the session.
    """
    if province and district and city:
        shipping_price = Shipping_Price(province, district, city)
        request.session['shipping_price'] = shipping_price
        request.session.modified = True
    return request.session.get('shipping_price', 400)

@login_required(login_url='login')
def cart(request):

    if request.htmx:
        form_type=request.POST.get("formtype")
        if form_type=="location":
        # Store shipping data in session
            province = request.POST.get("province")
            district = request.POST.get("district")
            city = request.POST.get("city")
            postcode=request.POST.get("postcode")
            print(province,district,city,postcode)
            not_updated=False ##!to check is value is selected or not
            if province=="" or district=="" or city=="":
                not_updated=True
            if province and district and city and postcode:
                request.session['shipping_data'] = {
                    'province': province,
                    'district':district,
                    'city': city,
                    'postcode': postcode
                }
                set_shipping_price_in_session(request,province,district,city)
            request.session.modified = True
            response = JsonResponse({"reload": True})
            response["HX-Refresh"] = "true"
            if not_updated:
                messages.error(request, "Shipping information and price have not been updated.")
            else:
                messages.success(request, "Shipping information and price have been successfully updated.")
            return response
        elif form_type=="coupon":
            coupon_code=request.POST.get("couponcode")
        
    cart_items = CartItem.objects.filter(user=request.user).select_related("product", "product__category")
    overall_subtotal = sum([
        (setattr(cart_item, 'subtotal', cart_item.product.price_after_discount * cart_item.quantity) or cart_item.subtotal)
        if cart_item.product.price_after_discount else
        (setattr(cart_item, 'subtotal', cart_item.product.price * cart_item.quantity) or cart_item.subtotal)
        for cart_item in cart_items
    ])

    shipping_price = request.session.get('shipping_price', 400)
    total_price=overall_subtotal+shipping_price
    context={
        'cart_items':cart_items,
        'subtotal':overall_subtotal,
        'shipping_price':shipping_price,
        'total_price':total_price,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'Cart', 'url': None},
        ],
        }
    
    return render(request,'shopapp/cart.html',context=context)
   

def add_remove_cart(request, slug):
    if not request.user.is_authenticated:
        if request.htmx:
            response = JsonResponse({"redirect": True})
            response["HX-Redirect"] = "/login/"
            return response
        return redirect('login')

    product = get_object_or_404(Product, slug=slug)
    if request.method == "POST":
        quantity = int(request.POST.get(f"quantity-{slug}", 1))
        selected_color = request.POST.get("selected_color", "")
        selected_size = request.POST.get("selected_size", "")

        if quantity > product.stock:
            return JsonResponse({
                ##!for toster
                "status": "error",
                "message": f"Only {product.stock} items available in stock.",
                ##!
                'success': False,
                'product_slug': slug,
            })

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, 
            product=product,
            defaults={
                'quantity': quantity,
                'color': selected_color,
                'size': selected_size,
            }
        )
        
        if not created:
            cart_item.quantity = quantity
            cart_item.color = selected_color
            cart_item.size = selected_size
            cart_item.save()

        # Calculate totals using string formatting for decimal values
        item_subtotal = cart_item.quantity * cart_item.product.price_after_discount
        cart_items = CartItem.objects.filter(user=request.user)
        cart_subtotal = sum(item.quantity * item.product.price_after_discount for item in cart_items)
        shipping_price = Decimal(request.session.get('shipping_price', 400))  # Use Decimal for consistency
        total_price = cart_subtotal + shipping_price

        return JsonResponse({
            ##!for toster
            "status": "success",
            "message": f"Product added to cart",
            ##!
            'success': True,
            'action': 'updated',
            'cart_count': cart_items.count(),
            'product_slug': slug,
            'item_quantity': cart_item.quantity,
            'item_subtotal': str(item_subtotal),  # Convert Decimal to string
            'cart_subtotal': str(cart_subtotal),
            'shipping_price': str(shipping_price),
            'total_price': str(total_price),
        })

    if request.method == "DELETE":
        cart_item = CartItem.objects.filter(user=request.user, product=product).first()
        if cart_item:
            cart_item.delete()

        cart_items = CartItem.objects.filter(user=request.user)
        cart_subtotal = sum([item.quantity * item.product.price_after_discount for item in cart_items])
        shipping_price = request.session.get('shipping_price', 400)
        total_price = cart_subtotal + shipping_price
        count = request.user.cart_items.count()

        return JsonResponse({
            ##!for toster
            "status": "success",
            "message": "Product removed from cart",
            ##!
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
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    # Generate breadcrumb data
    cart_items = CartItem.objects.filter(user=request.user).select_related("product", "product__category")
    # Check if cart is empty
    if not cart_items.exists():
        messages.error(request, "Your cart is empty. Please add items to your cart before proceeding.")
        return redirect('shop')  # Redirect to the shop page or any other appropriate page
    
    # Breadcrumb context
    breadcrumb_items = [
        {'title': 'Home', 'url': reverse('home')},
        {'title': 'Shop', 'url': reverse('shop')},
        {'title': 'Checkout', 'url': None}  # Current page doesn't need URL
    ]
    
    # Calculate prices
    cart_subtotal = sum(Decimal(item.total_price()) for item in cart_items)
    shipping_price = request.session.get('shipping_price', 400)
# Add logic for dynamic shipping
    total_price = cart_subtotal + shipping_price
    
    
    if request.method == "POST":
        name=request.POST.get("name")
        address=request.POST.get("address")
        city=request.POST.get("city")
        postcode=request.POST.get("postcode")
        phone=request.POST.get("phone")
        email=request.POST.get("email")
        payment_method=request.POST.get("payment_method")
        raw_order_note = request.POST.get("order_note", "")
        order_note = gangajal.validate(raw_order_note, 1) if raw_order_note else ""
        
        try:
            with transaction.atomic():
                # Create the Order
                order = Order.objects.create(
                    user=request.user,
                    total_price=total_price,
                    shipping_price=shipping_price,
                    customer_name=name,
                    customer_address=address,
                    city=city,
                    postcode=postcode,
                    phone=phone,
                    customer_email=email,
                    order_note=order_note,
                )

                # Create OrderItems from CartItems
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.total_price(),
                    )

                # Clear the cart after order is placed
                cart_items.delete()
                messages.success(request, "Order placed successfully!")

                if payment_method=="Esewa":
                    return redirect("esewa_checkout", order_id=order.id)
                if payment_method=="Khalti":
                    return redirect("khalti_checkout", order_id=order.id)
                if payment_method=="Paypal":
                    return redirect("paypal_checkout", order_id=order.id)
                if payment_method=="COD":
                    try:
                        with transaction.atomic():
                            Transaction.objects.create(
                                order=order,
                                user=request.user,
                                payment_method='COD',
                                amount=order.total_price,
                                status='Pending'
                            )
                            
                            order.status = "Pending"
                            order.payment = False
                            order.save()
                            
                            messages.success(request, "Your Cash on Delivery order has been placed.")
                            return redirect("user-dashboard")
                    except Exception as e:
                        messages.error(request, f"Error processing your order: {str(e)}")
                        return redirect("checkout")
                return redirect('shop')

        except Exception as e:
            messages.error(request, "There was an issue processing your order. Please try again.")
            return redirect('shop')
    ##removing session data stored in cart and passing for auto fill
    shipping_data = request.session.pop('shipping_data', None)
    if shipping_data:
        province = shipping_data.get('province')
        district = shipping_data.get('district')
        city = shipping_data.get('city')
        postcode = shipping_data.get('postcode')
    else:
        messages.error(request, "Shipping information is missing. Please fill out your shipping details.")
        return redirect('cart')
    
    context = {
        'address':province+" "+district,
        'city':city,
        'postcode':postcode,
        'breadcrumb_items': breadcrumb_items,
        'cart_items': cart_items,
        'cart_subtotal': cart_subtotal,
        'shipping_price': shipping_price,
        'total_price': total_price,
        'profile': profile,  # Pass the user profile to the template
    }
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
                messages.error(request, "Invalid payment data format")
                return redirect("checkout")
            
            # Verify payment status
            if payment_data.get('status') == 'COMPLETE':
                try:
                    with transaction.atomic():
                        Transaction.objects.create(
                            order=order,
                            user=request.user,
                            payment_method='Esewa',
                            amount=Decimal(str(payment_data.get('total_amount', '0').replace(',', ''))),
                            esewa_transaction_id=payment_data.get('transaction_uuid'),
                            status='Success'
                        )
                        
                        # Update order status without deducting stock yet
                        order.status = 'Pending'  # Start with pending
                        order.payment = True
                        order.save()
                        
                        messages.success(request, "Payment successful! Your order has been confirmed.")
                        return redirect("user-dashboard")
                except ValueError as e:
                    # Handle insufficient stock error
                    messages.error(request, str(e))
                    return redirect("checkout")
                    
            else:
                messages.error(request, "Payment was not completed successfully.")
                return redirect("checkout")
                
        except Exception as e:
            messages.error(request, "There was an error processing your payment.")
            return redirect("checkout")
            
    return redirect("user-dashboard")

def khalti(request):
    pass

def paypal(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    host = request.get_host()
    amount_usd = float(order.total_price) / settings.NPR_TO_USD_RATE
    amount_usd = round(amount_usd, 2)

    paypal_dict = {
        "cmd": "_xclick",
        "business": settings.PAYPAL_BUSINESS_EMAIL,  # Use business email from settings
        "amount": str(amount_usd),
        "item_name": f"Order #{order.id}",
        "invoice": str(order.id),
        "currency_code": settings.PAYPAL_CURRENCY,
        "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
        "return": request.build_absolute_uri(reverse('paypal-success', kwargs={'order_id': order.id})),
        "cancel_return": request.build_absolute_uri(reverse('checkout')),
    }

    form = PayPalPaymentsForm(initial=paypal_dict)
    context = {
        "order": order,
        "form": form,
        "amount_npr": order.total_price,
        "amount_usd": amount_usd
    }
    return render(request, "shopapp/paypal.html", context)

def paypal_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    try:
        with transaction.atomic():
            # Create transaction record
            Transaction.objects.create(
                order=order,
                user=request.user,
                payment_method='PayPal',
                amount=order.total_price,
                status='Success'
            )
            
            # Update order status without deducting stock yet
            order.status = "Pending"  # Start with pending
            order.payment = True
            order.save()
            
            messages.success(request, "Payment successful! Your order has been confirmed.")
            return redirect('user-dashboard')
    except ValueError as e:
        # Handle insufficient stock error
        messages.error(request, str(e))
        return redirect("checkout")

# def chat(request):
#     return render(request,'shopapp/chatbot.html')

@require_POST
def chat_bot(request):
    if request.method == "POST":
        user_message = request.POST.get('message', '').strip()
        if not user_message or len(user_message) > 500:
            return HttpResponseBadRequest("Invalid message")

        try:
            ollama_url = "http://localhost:11434/api/generate"
            
            system_prompt = """You are a shopping assistant. Keep responses very short and direct.

Store hours: 10 AM - 6 PM
Contact: +977-9876543210 
Returns: 7 days"""

            # Use a lighter model configuration
            payload = {
                "model": "llama2", # More optimized than Mistral for lower-end hardware
                "prompt": f"{system_prompt}\n\nQuestion: {user_message}\nAnswer:",
                "stream": False,
                "temperature": 0.1, # Lower temperature for faster, more focused responses
                "max_tokens": 30,   # Limit output size
                "top_k": 1,        # Reduce sampling options
                "top_p": 0.1,      # Further reduce variations
                "num_ctx": 512,     # Smaller context window
                "num_thread": 4,    # Limit threads for your CPU
                "stop": ["\n", "Question:", "Answer:"]
            }

            api_response = requests.post(ollama_url, json=payload, timeout=15)
            
            if api_response.status_code == 200:
                response_data = api_response.json()
                bot_response = response_data.get('response', '').strip()
                
                # Clean up response
                bot_response = bot_response.replace('Assistant:', '').strip()
                
                # Add period if missing
                if bot_response and not bot_response[-1] in '.!?':
                    bot_response += '.'
                
                # Fallback for empty responses
                if len(bot_response.split()) < 2:
                    bot_response = "How can I help you shop today?"

            response = HttpResponse(f"""
                <div class="chat__message user__message">
                    <div class="message__content">
                        <p>{user_message}</p>
                    </div>
                    <span class="message__time">Just now</span>
                </div>
                <div class="chat__message bot__message">
                    <div class="message__content">
                        <p>{bot_response}</p>
                    </div>
                    <span class="message__time">Just now</span>
                </div>
            """)
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        
        except requests.Timeout:
            logger.error("Ollama API timeout")
            bot_response = "Sorry, I'm taking longer than usual to respond. Please try again."
        except Exception as e:
            logger.error(f"Ollama API error: {str(e)}")
            bot_response = "Sorry, I encountered an error. Please try again."

        response = HttpResponse(f"""
            <div class="chat__message user__message">
                <div class="message__content">
                    <p>{user_message}</p>
                </div>
                <span class="message__time">Just now</span>
            </div>
            <div class="chat__message bot__message">
                <div class="message__content">
                    <p>{bot_response}</p>
                </div>
                <span class="message__time">Just now</span>
            </div>
        """)
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    
    return HttpResponseNotAllowed(["POST"])

@login_required(login_url='login')
def compare_view(request):
    compare_items = request.session.get('compare_items', [])
    products = Product.objects.filter(slug__in=compare_items)
    
    context = {
        'products': products,
        'breadcrumb_items': [
            {'title': 'Home', 'url': reverse('home')},
            {'title': 'Compare', 'url': None}
        ]
    }
    return render(request, 'shopapp/compare.html', context)

def add_remove_compare(request, slug):
    if not request.user.is_authenticated:
        return redirect('login')

    # Initialize compare list in session
    if 'compare_items' not in request.session:
        request.session['compare_items'] = []

    compare_items = request.session['compare_items']
    
    if (slug in compare_items):
        compare_items.remove(slug)
        messages.info(request, "Product removed from comparison")
    else:
        # FIFO: If already at max capacity, remove the oldest (first) item
        if len(compare_items) >= 4:
            removed_slug = compare_items.pop(0)  # Remove oldest (FIFO)
            messages.info(request, "Oldest product removed to add new one")
            return redirect('compare')
        compare_items.append(slug)
        messages.success(request, "Product added to comparison")
    
    # Save changes to session
    request.session['compare_items'] = compare_items
    request.session.modified = True
    
    # Always redirect to compare page after adding an item
    if len(compare_items) > 0:
        return redirect('compare')
    
    # Only return to shop if all items were removed
    return redirect('shop')

@login_required(login_url='login')
def generate_bill(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    # Allow bill generation only if there is a successful transaction for this order
    if not order.can_generate_bill():
        messages.error(request, "Bill can only be generated for orders with successful payment.")
        return redirect('user-dashboard')

    context = {
        'order': order,
        'show_print': True  # Flag to show print button
    }
    return render(request, 'shopapp/bill.html', context)


@login_required(login_url='login')
def profile_onboarding(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone_number = request.POST.get("phone_number")
        address = request.POST.get("address")
        profile_image = request.FILES.get("profile_image")

        if username:
            # Username validation: check if already taken (excluding current user)
            if User.objects.filter(username=username).exclude(pk=request.user.pk).exists():
                messages.error(request, "Username already taken!")
            else:
                request.user.username = username
                request.user.save()
        if email:
            # Email validation: must match pattern and not already in use (excluding current user)
            if not re.fullmatch(r'^[A-Za-z][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
                messages.error(request, "Invalid email format. Email cannot start with a number.")
            elif User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, "Email already in use!")
            else:
                request.user.email = email
                request.user.save()
        if phone_number:
            mobile_regex = r"^(97|98)\d{7,8}$"
            landline_regex = r"^(01|04|05|06|07)\d{6,7}$"
            if not (re.match(mobile_regex, phone_number) or re.match(landline_regex, phone_number)):
                messages.error(request, "Enter a valid Nepali phone number.")
            else:
                profile.phone_number = phone_number
        if address:
            profile.address = address
        if profile_image:
            if not profile_image.name.lower().endswith(('jpeg', 'png', 'jpg')):
                messages.error(request, "Only JPEG, PNG, and JPG image formats are allowed.")
            else:
                profile.profile_image = profile_image
        profile.save()

        messages.success(request, "Profile setup completed successfully!")
        return redirect("user-dashboard")

    context = {
        "user": request.user,
        "profile": profile,
        "onboarding": True
    }
    return render(request, "shopapp/profilesetup.html", context)

def forgot_password(request):
    message = []
    if request.method == "POST":
        # Fix: Use the correct POST key for Turnstile response
        token = request.POST.get("cf-turnstile-response") or request.POST.get("cf_turnstile_response")
        if not token:
            message.append("Captcha verification failed! Please try again.")
            return render(request, "shopapp/forgot-password.html", {"message": message})
        verification = verify_turnstile(token)
        if verification.get("success"):
            email = request.POST.get("email")
            # Email validation
            if not re.fullmatch(r'^[A-Za-z][A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
                messages.error(request, "Invalid email format. Email cannot start with a number.")
                return render(request, "shopapp/forgot-password.html", {"message": message})
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse("reset-password") + f"?uid={user.pk}&token={token}"
                )
                subject = "Password Reset Request"
                text_content = f"Click the link to reset your password: {reset_url}"
                
                # Use an externally hosted logo image URL
                logo_url = "https://i.imgur.com/2kLUNbL.png"
                
                html_content = f"""
                    <div style="max-width: 600px; margin: auto; font-family: Arial, sans-serif; border-radius: 8px; overflow: hidden; background-color: #f4f4f9; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                    <div style="background-color: #000; padding: 20px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;">
                        <img src="{logo_url}" alt="BIKRENTE Logo" style="width: 120px; height: auto; margin-bottom: 10px;">
                        <h1 style="color: #fff; font-size: 24px; margin: 0;">BIKRENTE</h1>
                    </div>
                    <div style="padding: 20px; background-color: #ffffff;">
                        <h2 style="color: #333; font-size: 20px; margin-bottom: 10px;">Password Reset Request</h2>
                        <p style="color: #555; font-size: 16px; margin-bottom: 20px;">Hello <b>{user.username}</b>,</p>
                        <p style="color: #555; font-size: 16px; margin-bottom: 20px;">We received a request to reset your password. Click the button below to reset it:</p>
                        <p style="text-align: center; margin-bottom: 20px;">
                        <a href="{reset_url}" style="background-color: #4a90e2; color: #fff; padding: 12px 24px; border-radius: 5px; text-decoration: none; font-size: 16px; font-weight: bold;">
                            Reset Password
                        </a>
                        </p>
                        <p style="color: #555; font-size: 14px; margin-bottom: 20px;">If you did not request this, you can safely ignore this email.</p>
                    </div>
                    <div style="background-color: #f9f9f9; padding: 15px; text-align: center; font-size: 12px; color: #777; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;">
                        <p>This link will expire soon for your security.</p>
                        <p>© {timezone.now().year} BIKRENTE. All rights reserved.</p>
                        <p>This is an automated email. Please do not reply.</p>
                    </div>
                    </div>
                """
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                email_msg.attach_alternative(html_content, "text/html")
                email_msg.send()
                message.append("If an account with that email exists, a password reset link has been sent.")
            except User.DoesNotExist:
                # Do not reveal if the email exists for security reasons
                message.append("If an account with that email exists, a password reset link has been sent.")
            return render(request, "shopapp/forgot-password.html", {"message": message})
        else:
            message.append("Captcha failed!")
            return render(request, "shopapp/forgot-password.html", {"message": message})
    return render(request, "shopapp/forgot-password.html")

def reset_password(request):
    uid = request.GET.get("uid")
    token = request.GET.get("token")
    message = []
    user = None
    if uid and token:
        try:
            user = User.objects.get(pk=uid)
            if not default_token_generator.check_token(user, token):
                user = None
        except User.DoesNotExist:
            user = None
    if request.method == "POST" and user:
        password = request.POST.get("password")
        cpassword = request.POST.get("cpassword")
        if password == cpassword and len(password) >= 8:
            user.password = make_password(password)
            user.save()
            message.append("Password reset successful. You can now log in.")
            return redirect("login")
        else:
            message.append("Passwords do not match or are too short.")
    return render(request, "shopapp/reset-password.html", {"user": user, "message": message})

def helloworld(request):
    return render(request,'shopapp/helloworld.html')
def custom_404(request, exception):
    return render(request, 'shopapp/includes/caseno404.html', status=404)

handler404 = custom_404

def subscribe_newsletter(request):
    """
    Handles newsletter subscription with HTMX support.
    """
    if request.method == "POST":
        email = request.POST.get("email")
        email_regex = r'^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z{2,}$'
        if email and re.match(email_regex, email):
            subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                return HttpResponse('<p class="newsletter__description success-message">Subscribed successfully!</p>')
            else:
                return HttpResponse('<p class="newsletter__description info-message">Already subscribed.</p>')
        else:
            return HttpResponse('<p class="newsletter__description error-message">Invalid email address.</p>', status=400)
    return HttpResponse('<p class="newsletter__description error-message">Invalid request.</p>', status=400)