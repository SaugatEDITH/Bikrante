from django.shortcuts import render, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import login
message=[]
def home(request):
    context = {
        'is_home': True
    }
    return render(request, 'shopapp/index.html', context)

def shop(request):
    context = {
        'is_home': False
    }
    return render(request, 'shopapp/products-card.html', context)

def login(request):
    
    context = {
        'is_login': True,  # Add this to determine which form to show
        'is_register': False
    }
    return render(request, 'shopapp/login-register.html', context)

def signup(request):
    if request.method=='POST':
        username=request.POST.get('username')
        email=request.POST.get('email')
        password=request.POST.get('password')
        confirm_password=request.POST.get('cpassword')
        if password != confirm_password:
            message.append("Passwords do not match.")
            context={'message':message}
            return render(request,'shopapp/login-register.html')
        if User.objects.filter(username=username).exists():
            message.append("Username already taken!")
            context={'message':message}
            return render(request,'shopapp/login-register.html')
        if User.objects.filter(email=email).exists():
            message.append("Email already in use !")
            return render(request,'shopapp')
    context = {
        'is_login': False,
        'is_register': True
    }
    return render(request, 'shopapp/login-register.html', context)
def shop(request):
    return render(request,"shopapp/shop.html")