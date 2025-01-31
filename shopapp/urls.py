from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('shop/', views.shop, name='shop'),
    path('cart/',views.cart,name='cart'),
    path('contact/', views.contact, name='contact'),
    path('wishlist/',views.wishlist,name="wishlist"),
    path('user-dashboard/',views.user_dashboard,name='user-dashboard'),
    path('category/<slug:slug>/', views.category_detail, name='category-detail'),
    path('product/<slug:slug>/', views.product_detail, name='product-detail'),
    path('search/',views.search,name="search")
]