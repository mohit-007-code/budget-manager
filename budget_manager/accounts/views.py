from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomLoginForm

@ensure_csrf_cookie
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created successfully.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Registration failed. Please correct the errors below.')
    
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form' : form})

@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome {user.username}! ')

                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password')
    else:
            form = CustomLoginForm()

    return render(request, 'accounts/login.html' ,{'form': form})
    
def logout_view(request):
    username = request.user.username
    logout(request)
    messages.success(request, f'Goodbye {username}! You have been logged out successfully.')
    return redirect('accounts:login')


@ensure_csrf_cookie
def csrf_test(request):
    """Diagnostic endpoint: returns the CSRF token and ensures the cookie is set.

    Visit /accounts/csrf-test/ and check the response JSON and the Network tab for
    a Set-Cookie header for 'csrftoken'. This helps debug why CSRF verification
    fails on form POSTs.
    """
    token = get_token(request)
    return JsonResponse({'csrf_token': token})
    