"""
Routes app views - home, listing, detail, favorites, reviews, map.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.conf import settings

from .models import Route, Category, Review, Favorite, RouteView, RoutePoint
from .forms import ReviewForm, RouteSearchForm
from apps.recommendations.engine import get_recommendations


def home_view(request):
    """Homepage with featured routes, map, and search."""
    featured_routes = Route.objects.filter(
        status='active', is_featured=True
    ).select_related('category').prefetch_related('gallery')[:6]

    popular_routes = Route.objects.filter(
        status='active'
    ).order_by('-booking_count')[:8]

    categories = Category.objects.annotate(
        route_count=Count('routes', filter=Q(routes__status='active'))
    ).filter(route_count__gt=0)

    # Routes for map (all active with coordinates)
    map_routes = Route.objects.filter(
        status='active',
        start_lat__isnull=False
    ).values(
        'id', 'title', 'slug', 'start_lat', 'start_lng',
        'difficulty', 'distance_km', 'duration_hours', 'avg_rating'
    )

    return render(request, 'routes/home.html', {
        'featured_routes': featured_routes,
        'popular_routes': popular_routes,
        'categories': categories,
        'map_routes': list(map_routes),
        'map_lat': settings.MAP_DEFAULT_LAT,
        'map_lng': settings.MAP_DEFAULT_LNG,
        'map_zoom': settings.MAP_DEFAULT_ZOOM,
    })


def route_list_view(request):
    """Route listing with search, filters, sorting."""
    routes = Route.objects.filter(status='active').select_related('category')

    # Search
    query = request.GET.get('q', '')
    if query:
        routes = routes.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query)
        )

    # Filters
    category = request.GET.get('category')
    if category:
        routes = routes.filter(category__slug=category)

    difficulty = request.GET.get('difficulty')
    if difficulty:
        routes = routes.filter(difficulty=difficulty)

    min_distance = request.GET.get('min_distance')
    max_distance = request.GET.get('max_distance')
    if min_distance:
        routes = routes.filter(distance_km__gte=float(min_distance))
    if max_distance:
        routes = routes.filter(distance_km__lte=float(max_distance))

    max_price = request.GET.get('max_price')
    if max_price:
        routes = routes.filter(Q(price__lte=float(max_price)) | Q(price__isnull=True))

    free_only = request.GET.get('free_only')
    if free_only:
        routes = routes.filter(price__isnull=True)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    sort_options = {
        'popular': '-booking_count',
        'rating': '-avg_rating',
        'price_asc': 'price',
        'price_desc': '-price',
        'distance': 'distance_km',
        'new': '-created_at',
    }
    routes = routes.order_by(sort_options.get(sort, '-created_at'))

    # Pagination
    paginator = Paginator(routes, settings.ROUTES_PER_PAGE)
    page = request.GET.get('page', 1)
    routes_page = paginator.get_page(page)

    # For map
    map_routes = list(Route.objects.filter(
        status='active', start_lat__isnull=False
    ).values('id', 'title', 'slug', 'start_lat', 'start_lng', 'difficulty'))

    categories = Category.objects.annotate(
        route_count=Count('routes', filter=Q(routes__status='active'))
    )

    return render(request, 'routes/list.html', {
        'routes': routes_page,
        'categories': categories,
        'map_routes': map_routes,
        'query': query,
        'current_category': category,
        'current_difficulty': difficulty,
        'current_sort': sort,
        'total_count': paginator.count,
        'map_lat': settings.MAP_DEFAULT_LAT,
        'map_lng': settings.MAP_DEFAULT_LNG,
        'map_zoom': settings.MAP_DEFAULT_ZOOM,
    })


def route_detail_view(request, slug):
    """Route detail page with map, gallery, reviews."""
    route = get_object_or_404(Route, slug=slug, status='active')

    # Track view
    if request.user.is_authenticated:
        RouteView.objects.get_or_create(user=request.user, route=route)
    else:
        session_key = request.session.session_key or ''
        if session_key:
            RouteView.objects.get_or_create(session_key=session_key, route=route, user=None)
    route.view_count = RouteView.objects.filter(route=route).count()
    Route.objects.filter(pk=route.pk).update(view_count=route.view_count)

    # Points for map
    points = route.points.all().order_by('order')

    # Reviews
    reviews = route.reviews.filter(is_approved=True).select_related('user').order_by('-created_at')
    paginator = Paginator(reviews, 10)
    page = request.GET.get('page', 1)
    reviews_page = paginator.get_page(page)

    # Review form
    user_review = None
    review_form = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(route=route, user=request.user).first()
        if not user_review:
            review_form = ReviewForm()

    # Favorites
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, route=route).exists()

    # Recommendations
    recommended = get_recommendations(request.user if request.user.is_authenticated else None, route, limit=4)

    return render(request, 'routes/detail.html', {
        'route': route,
        'points': points,
        'reviews': reviews_page,
        'review_form': review_form,
        'user_review': user_review,
        'is_favorite': is_favorite,
        'recommended': recommended,
        'gallery': route.gallery.all(),
    })


@login_required
@require_POST
def add_review_view(request, slug):
    """AJAX: Submit a review for a route."""
    route = get_object_or_404(Route, slug=slug, status='active')

    if Review.objects.filter(route=route, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Вы уже оставили отзыв.'})

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.route = route
        review.user = request.user
        review.save()
        route.update_rating()
        return JsonResponse({
            'success': True,
            'review': {
                'rating': review.rating,
                'comment': review.comment,
                'user': request.user.get_full_name() or request.user.username,
                'avatar': request.user.avatar_url,
                'created_at': review.created_at.strftime('%d.%m.%Y'),
            }
        })
    return JsonResponse({'success': False, 'errors': form.errors})


@login_required
@require_POST
def toggle_favorite_view(request, slug):
    """AJAX: Toggle route favorite."""
    route = get_object_or_404(Route, slug=slug)
    favorite, created = Favorite.objects.get_or_create(user=request.user, route=route)
    if not created:
        favorite.delete()
        return JsonResponse({'success': True, 'is_favorite': False})
    return JsonResponse({'success': True, 'is_favorite': True})


def map_view(request):
    """Full-screen interactive map with all routes and places."""
    routes = list(Route.objects.filter(
        status='active', start_lat__isnull=False
    ).values(
        'id', 'title', 'slug', 'start_lat', 'start_lng',
        'end_lat', 'end_lng', 'difficulty', 'distance_km',
        'duration_hours', 'avg_rating', 'route_geojson',
        'category__name', 'category__color'
    ))

    from apps.places.models import Place
    places = list(Place.objects.filter(
        is_active=True, lat__isnull=False
    ).values('id', 'name', 'slug', 'lat', 'lng', 'category__name', 'category__icon'))

    categories = list(Category.objects.values('id', 'name', 'color'))

    return render(request, 'routes/map.html', {
        'routes': routes,
        'places': places,
        'categories': categories,
        'map_lat': settings.MAP_DEFAULT_LAT,
        'map_lng': settings.MAP_DEFAULT_LNG,
        'map_zoom': settings.MAP_DEFAULT_ZOOM,
    })


def route_geojson_api(request, slug):
    """API: Return GeoJSON for a specific route."""
    route = get_object_or_404(Route, slug=slug)
    points = list(route.points.order_by('order').values('lat', 'lng', 'name', 'point_type'))

    geojson = {
        'type': 'FeatureCollection',
        'features': []
    }

    # Add route path
    if route.route_geojson:
        geojson['features'].append({
            'type': 'Feature',
            'geometry': route.route_geojson,
            'properties': {
                'type': 'route',
                'title': route.title,
                'difficulty': route.difficulty,
            }
        })
    elif len(points) >= 2:
        coords = [[p['lng'], p['lat']] for p in points]
        geojson['features'].append({
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'type': 'route', 'title': route.title}
        })

    # Add points
    for point in points:
        geojson['features'].append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [point['lng'], point['lat']]},
            'properties': {
                'type': 'waypoint',
                'name': point['name'],
                'point_type': point['point_type'],
            }
        })

    return JsonResponse(geojson)


def all_routes_geojson_api(request):
    """API: Return GeoJSON for all active routes (for map)."""
    routes = Route.objects.filter(status='active', start_lat__isnull=False)
    features = []

    for route in routes:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [route.start_lng, route.start_lat]
            },
            'properties': {
                'id': str(route.id),
                'title': route.title,
                'slug': route.slug,
                'difficulty': route.difficulty,
                'difficulty_label': route.difficulty_label,
                'distance_km': route.distance_km,
                'duration_hours': route.duration_hours,
                'avg_rating': route.avg_rating,
                'url': route.get_absolute_url(),
            }
        })

    return JsonResponse({'type': 'FeatureCollection', 'features': features})


def context_processors(request):
    return {}


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)