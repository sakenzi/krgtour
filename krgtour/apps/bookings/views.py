"""
Bookings app views.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Booking
from .forms import BookingForm
from apps.routes.models import Route
from apps.users.models import Notification


@login_required
def create_booking_view(request, route_slug):
    route = get_object_or_404(Route, slug=route_slug, status='active')

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.route = route

            # Calculate price
            if route.price:
                booking.total_price = route.price * booking.num_people
            else:
                booking.total_price = 0

            booking.save()

            # Update route stats
            Route.objects.filter(pk=route.pk).update(
                booking_count=route.bookings.count()
            )

            # Create notification
            Notification.objects.create(
                user=request.user,
                type='booking_confirmed',
                title='Бронирование создано',
                message=f'Ваше бронирование #{booking.confirmation_code} на маршрут "{route.title}" создано и ожидает подтверждения.',
                link=f'/bookings/{booking.id}/',
            )

            messages.success(request, f'Бронирование #{booking.confirmation_code} успешно создано!')
            return redirect('bookings:detail', pk=booking.id)
    else:
        # Pre-fill contact info
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'contact_name': request.user.get_full_name() or request.user.username,
                'contact_email': request.user.email,
                'contact_phone': request.user.phone,
            }
        form = BookingForm(initial=initial)

    return render(request, 'bookings/create.html', {
        'route': route,
        'form': form,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def booking_detail_view(request, pk):
    booking = get_object_or_404(Booking, id=pk, user=request.user)
    return render(request, 'bookings/detail.html', {'booking': booking})


@login_required
@require_POST
def cancel_booking_view(request, pk):
    booking = get_object_or_404(Booking, id=pk, user=request.user)
    if booking.can_cancel:
        booking.status = 'cancelled'
        booking.save()

        Notification.objects.create(
            user=request.user,
            type='booking_cancelled',
            title='Бронирование отменено',
            message=f'Ваше бронирование #{booking.confirmation_code} отменено.',
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.info(request, 'Бронирование отменено.')
    else:
        messages.error(request, 'Нельзя отменить это бронирование.')

    return redirect('users:bookings_history')


@login_required
def calculate_price_api(request):
    """AJAX: Calculate booking price."""
    route_id = request.GET.get('route_id')
    num_people = int(request.GET.get('num_people', 1))

    try:
        route = Route.objects.get(id=route_id)
        if route.price:
            total = float(route.price) * num_people
        else:
            total = 0
        return JsonResponse({'total': total, 'currency': '₸'})
    except Route.DoesNotExist:
        return JsonResponse({'error': 'Route not found'}, status=404)