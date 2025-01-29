from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
import re

def home(request):
    context = {
        'is_home': True
    }
    return render(request, 'shopapp/index.html', context)

def shop(request):
    context = {
        'is_home': False
    }
    return render(request, 'shopapp/shop.html', context)

def login(request):
    context = {
        'is_login': True,
        'is_register': False,
        'message': []
    }
    if request.method == 'POST':
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
    return render(request, 'shopapp/login-register.html', context)

def signup(request):
    context = {
        'is_login': False,
        'is_register': True,
        'message': []
    }
    if request.method == 'POST':
        print("POST request received")  # Debug print
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
        if not re.fullmatch(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
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
        print(f"Context messages: {context['message']}")  # Debug print
    return render(request, 'shopapp/login-register.html', context)

@login_required
def user_logout(request):
    logout(request)
    return redirect('home')

def contact(request):
    return render(request, 'shopapp/contact.html')

@login_required
def user_dashboard(request):
    context={
        'message':[]
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
    return render(request,'shopapp/user-dashboard.html')