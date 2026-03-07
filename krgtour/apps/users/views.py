"""
Users app views - registration, login, profile, favorites, notifications.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Count

from .models import User, Notification
from .forms import (
    UserRegistrationForm, UserLoginForm,
    UserProfileForm, UserPasswordChangeForm
)
from apps.routes.models import Route, Favorite as RouteFavorite
from apps.places.models import Place, PlaceFavorite
from apps.bookings.models import Booking


def register_view(request):
    if request.user.is_authenticated:
        return redirect('routes:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name() or user.username}!')
            return redirect('routes:home')
    else:
        form = UserRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('routes:home')

    next_url = request.GET.get('next', '/')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'С возвращением, {user.get_full_name() or user.username}!')
            return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('routes:home')


@login_required
def profile_view(request):
    user = request.user
    recent_bookings = Booking.objects.filter(user=user).order_by('-created_at')[:5]
    stats = {
        'total_bookings': Booking.objects.filter(user=user).count(),
        'completed_bookings': Booking.objects.filter(user=user, status='completed').count(),
        'favorite_routes': RouteFavorite.objects.filter(user=user).count(),
        'favorite_places': PlaceFavorite.objects.filter(user=user).count(),
    }
    return render(request, 'users/profile.html', {
        'user': user,
        'recent_bookings': recent_bookings,
        'stats': stats,
    })


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён!')
            return redirect('users:profile')
    else:
        form = UserPasswordChangeForm(request.user)

    return render(request, 'users/change_password.html', {'form': form})


@login_required
def favorites_view(request):
    route_favorites = RouteFavorite.objects.filter(
        user=request.user
    ).select_related('route').order_by('-created_at')

    place_favorites = PlaceFavorite.objects.filter(
        user=request.user
    ).select_related('place').order_by('-created_at')

    return render(request, 'users/favorites.html', {
        'route_favorites': route_favorites,
        'place_favorites': place_favorites,
    })


@login_required
def bookings_history_view(request):
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related('route').order_by('-created_at')

    paginator = Paginator(bookings, 10)
    page = request.GET.get('page', 1)
    bookings_page = paginator.get_page(page)

    return render(request, 'users/bookings_history.html', {
        'bookings': bookings_page,
    })


@login_required
def notifications_view(request):
    notifications = request.user.notifications.all()
    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)

    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)
    notifications_page = paginator.get_page(page)

    return render(request, 'users/notifications.html', {
        'notifications': notifications_page,
    })


@login_required
def notifications_count_api(request):
    """AJAX endpoint for unread notification count."""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


def public_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    reviews = user.reviews.filter(is_approved=True).select_related('route')[:10]
    return render(request, 'users/public_profile.html', {
        'profile_user': user,
        'reviews': reviews,
    })