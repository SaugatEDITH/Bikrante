from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('shop/', views.shop, name='shop'),
    path('contact/', views.contact, name='contact'),
    path('user-dashboard/',views.user_dashboard,name='user-dashboard'),
]