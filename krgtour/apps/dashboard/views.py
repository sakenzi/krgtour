"""
Custom admin dashboard views.
Accessible at /dashboard/ - requires staff access.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from apps.routes.models import Route, Category, Review, RoutePoint
from apps.routes.forms import RouteAdminForm
from apps.places.models import Place, PlaceCategory
from apps.bookings.models import Booking
from apps.users.models import User


@staff_member_required
def dashboard_home(request):
    """Main dashboard with stats overview."""
    today = timezone.now().date()
    last_month = today - timedelta(days=30)

    stats = {
        'total_routes': Route.objects.filter(status='active').count(),
        'total_places': Place.objects.filter(is_active=True).count(),
        'total_users': User.objects.count(),
        'total_bookings': Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'revenue': Booking.objects.filter(
            status__in=['confirmed', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'new_users_month': User.objects.filter(date_joined__date__gte=last_month).count(),
        'new_bookings_month': Booking.objects.filter(created_at__date__gte=last_month).count(),
    }

    recent_bookings = Booking.objects.select_related('user', 'route').order_by('-created_at')[:10]
    pending_reviews = Review.objects.filter(is_approved=False).select_related('user', 'route')[:10]
    top_routes = Route.objects.filter(status='active').order_by('-booking_count')[:5]

    # Bookings by day (last 7 days)
    booking_chart = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        count = Booking.objects.filter(created_at__date=date).count()
        booking_chart.append({'date': date.strftime('%d.%m'), 'count': count})

    return render(request, 'dashboard/home.html', {
        'stats': stats,
        'recent_bookings': recent_bookings,
        'pending_reviews': pending_reviews,
        'top_routes': top_routes,
        'booking_chart': booking_chart,
    })


@staff_member_required
def route_list_dashboard(request):
    routes = Route.objects.select_related('category').order_by('-created_at')
    return render(request, 'dashboard/routes/list.html', {'routes': routes})


@staff_member_required
def route_create_dashboard(request):
    if request.method == 'POST':
        form = RouteAdminForm(request.POST, request.FILES)
        if form.is_valid():
            route = form.save(commit=False)
            route.created_by = request.user
            route.save()

            # Handle route points from map
            points_data = request.POST.get('route_points_json', '[]')
            import json
            try:
                points = json.loads(points_data)
                for i, point in enumerate(points):
                    RoutePoint.objects.create(
                        route=route,
                        name=point.get('name', f'Точка {i+1}'),
                        lat=point['lat'],
                        lng=point['lng'],
                        order=i,
                        point_type=point.get('type', 'waypoint'),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

            messages.success(request, f'Маршрут "{route.title}" создан!')
            return redirect('dashboard:route_edit', slug=route.slug)
    else:
        form = RouteAdminForm()

    categories = Category.objects.all()
    return render(request, 'dashboard/routes/edit.html', {
        'form': form,
        'categories': categories,
        'is_create': True,
    })


@staff_member_required
def route_edit_dashboard(request, slug):
    route = get_object_or_404(Route, slug=slug)

    if request.method == 'POST':
        form = RouteAdminForm(request.POST, request.FILES, instance=route)
        if form.is_valid():
            route = form.save()

            # Update route points from map
            points_data = request.POST.get('route_points_json', '')
            if points_data:
                import json
                try:
                    points = json.loads(points_data)
                    RoutePoint.objects.filter(route=route).delete()
                    for i, point in enumerate(points):
                        RoutePoint.objects.create(
                            route=route,
                            name=point.get('name', f'Точка {i+1}'),
                            lat=point['lat'],
                            lng=point['lng'],
                            order=i,
                            point_type=point.get('type', 'waypoint'),
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

            messages.success(request, 'Маршрут обновлён!')
            return redirect('dashboard:route_edit', slug=route.slug)
    else:
        form = RouteAdminForm(instance=route)

    existing_points = list(route.points.order_by('order').values('name', 'lat', 'lng', 'point_type', 'order'))
    categories = Category.objects.all()

    return render(request, 'dashboard/routes/edit.html', {
        'form': form,
        'route': route,
        'existing_points': existing_points,
        'categories': categories,
        'is_create': False,
        'gallery': route.gallery.all(),
    })


@staff_member_required
@require_POST
def route_delete_dashboard(request, slug):
    route = get_object_or_404(Route, slug=slug)
    route.status = 'archived'
    route.save()
    messages.success(request, f'Маршрут "{route.title}" архивирован.')
    return redirect('dashboard:route_list')


@staff_member_required
def bookings_dashboard(request):
    status_filter = request.GET.get('status', '')
    bookings = Booking.objects.select_related('user', 'route').order_by('-created_at')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    return render(request, 'dashboard/bookings/list.html', {
        'bookings': bookings,
        'status_filter': status_filter,
    })


@staff_member_required
@require_POST
def update_booking_status(request, pk):
    import json
    booking = get_object_or_404(Booking, id=pk)
    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status in ['confirmed', 'completed', 'cancelled']:
        booking.status = new_status
        booking.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid status'})


@staff_member_required
def reviews_dashboard(request):
    reviews = Review.objects.select_related('user', 'route').order_by('-created_at')
    return render(request, 'dashboard/reviews/list.html', {'reviews': reviews})


@staff_member_required
@require_POST
def moderate_review(request, pk):
    import json
    review = get_object_or_404(Review, id=pk)
    data = json.loads(request.body)
    action = data.get('action')
    if action == 'approve':
        review.is_approved = True
        review.save()
        review.route.update_rating()
        return JsonResponse({'success': True})
    elif action == 'reject':
        review.is_approved = False
        review.save()
        return JsonResponse({'success': True})
    elif action == 'delete':
        review.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@staff_member_required
def upload_route_image(request, slug):
    """AJAX: Upload image to route gallery."""
    if request.method == 'POST' and request.FILES.get('image'):
        from apps.routes.models import RouteImage
        route = get_object_or_404(Route, slug=slug)
        img = RouteImage.objects.create(
            route=route,
            image=request.FILES['image'],
            caption=request.POST.get('caption', ''),
        )
        return JsonResponse({
            'success': True,
            'image_url': img.image.url,
            'id': img.id,
        })
    return JsonResponse({'success': False}, status=400)