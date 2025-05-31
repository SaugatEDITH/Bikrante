import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Bikrante.settings")

import django
django.setup()  # <-- Add this line to ensure apps are loaded

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

@pytest.mark.django_db
def test_home_view(client):
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_shop_view(client):
    url = reverse('shop')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_login_view_get(client):
    url = reverse('login')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_signup_view_get(client):
    url = reverse('signup')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_contact_view(client):
    url = reverse('contact')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_profile_onboarding_view_authenticated(client):
    user = User.objects.create_user(username="testuser", password="testpass")
    client.login(username="testuser", password="testpass")
    url = reverse('profile-onboarding')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_user_dashboard_view_authenticated(client):
    user = User.objects.create_user(username="testuser2", password="testpass2")
    client.login(username="testuser2", password="testpass2")
    url = reverse('user-dashboard')
    response = client.get(url)
    assert response.status_code == 200

@pytest.mark.django_db
def test_logout_view(client):
    user = User.objects.create_user(username="logoutuser", password="logoutpass")
    client.login(username="logoutuser", password="logoutpass")
    url = reverse('logout')
    response = client.get(url)
    assert response.status_code == 302  # Should redirect

@pytest.mark.django_db
def test_wishlist_requires_login(client):
    url = reverse('wishlist')
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login

@pytest.mark.django_db
def test_search_view(client):
    url = reverse('search')
    response = client.get(url)
    assert response.status_code == 200

# ...add more view tests as needed...
