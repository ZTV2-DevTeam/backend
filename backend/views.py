from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def config_wizard(request):
    """Configuration wizard view for initial system setup."""
    return render(request, 'config_wizard.html')