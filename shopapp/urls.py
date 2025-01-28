from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='log-out'),
    path('signup/', views.signup, name='signup'),
    path('shop', views.shop, name='shop'),
    path('contact/', views.contact, name='contact'),
]