"""
Routes app views - home, listing, detail, favorites, reviews, map.
"""

import json
from decimal import Decimal

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


class DecimalEncoder(json.JSONEncoder):
    """Конвертирует Decimal в float при сериализации."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _serialize_routes_for_map(routes_qs):
    """Превращает queryset маршрутов в список словарей для JSON."""
    result = []
    for r in routes_qs:
        start_lat = r.get('start_lat') or getattr(r, 'start_lat', None)
        start_lng = r.get('start_lng') or getattr(r, 'start_lng', None)
        if start_lat is None or start_lng is None:
            continue
        try:
            result.append({
                'slug':           str(r.get('slug', '') or getattr(r, 'slug', '')),
                'title':          str(r.get('title', '') or getattr(r, 'title', '')),
                'difficulty':     str(r.get('difficulty', '') or getattr(r, 'difficulty', '')),
                'distance_km':    float(r.get('distance_km') or getattr(r, 'distance_km', 0) or 0),
                'duration_hours': float(r.get('duration_hours') or getattr(r, 'duration_hours', 0) or 0),
                'avg_rating':     float(r.get('avg_rating') or getattr(r, 'avg_rating', None) or 0) or None,
                'start_lat':      float(start_lat),
                'start_lng':      float(start_lng),
            })
        except (TypeError, ValueError):
            continue
    return result


def _serialize_places_for_map(places_qs):
    """Превращает queryset мест в список словарей для JSON."""
    result = []
    for p in places_qs:
        lat = p.get('lat') or getattr(p, 'lat', None)
        lng = p.get('lng') or getattr(p, 'lng', None)
        if lat is None or lng is None:
            continue
        try:
            result.append({
                'slug':          str(p.get('slug', '') or getattr(p, 'slug', '')),
                'name':          str(p.get('name', '') or getattr(p, 'name', '')),
                'lat':           float(lat),
                'lng':           float(lng),
                'icon':          str(p.get('category__icon') or getattr(p, 'icon', '📍') or '📍'),
                'category_name': str(p.get('category__name') or ''),
                'avg_rating':    float(p.get('avg_rating') or getattr(p, 'avg_rating', None) or 0) or None,
            })
        except (TypeError, ValueError):
            continue
    return result


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

    map_routes_qs = Route.objects.filter(
        status='active',
        start_lat__isnull=False
    ).values('title', 'slug', 'start_lat', 'start_lng', 'difficulty', 'distance_km', 'duration_hours', 'avg_rating')

    map_routes_list = _serialize_routes_for_map(map_routes_qs)

    return render(request, 'routes/home.html', {
        'featured_routes': featured_routes,
        'popular_routes': popular_routes,
        'categories': categories,
        'map_routes_json': json.dumps(map_routes_list, ensure_ascii=False, cls=DecimalEncoder),
        'map_lat':  getattr(settings, 'MAP_DEFAULT_LAT', 49.8047),
        'map_lng':  getattr(settings, 'MAP_DEFAULT_LNG', 73.1094),
        'map_zoom': getattr(settings, 'MAP_DEFAULT_ZOOM', 11),
    })


def route_list_view(request):
    """Route listing with search, filters, sorting."""
    routes = Route.objects.filter(status='active').select_related('category')

    query = request.GET.get('q', '')
    if query:
        routes = routes.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query)
        )

    category = request.GET.get('category')
    if category:
        routes = routes.filter(category__slug=category)

    difficulty = request.GET.get('difficulty')
    if difficulty:
        routes = routes.filter(difficulty=difficulty)

    min_distance = request.GET.get('min_distance')
    max_distance = request.GET.get('max_distance')
    if min_distance:
        try:
            routes = routes.filter(distance_km__gte=float(min_distance))
        except ValueError:
            pass
    if max_distance:
        try:
            routes = routes.filter(distance_km__lte=float(max_distance))
        except ValueError:
            pass

    max_price = request.GET.get('max_price')
    if max_price:
        try:
            routes = routes.filter(Q(price__lte=float(max_price)) | Q(price__isnull=True))
        except ValueError:
            pass

    free_only = request.GET.get('free_only')
    if free_only:
        routes = routes.filter(price__isnull=True)

    sort = request.GET.get('sort', '-created_at')
    sort_options = {
        'popular':    '-booking_count',
        'rating':     '-avg_rating',
        'price_asc':  'price',
        'price_desc': '-price',
        'distance':   'distance_km',
        'new':        '-created_at',
    }
    routes = routes.order_by(sort_options.get(sort, '-created_at'))

    paginator = Paginator(routes, getattr(settings, 'ROUTES_PER_PAGE', 12))
    page = request.GET.get('page', 1)
    routes_page = paginator.get_page(page)

    map_routes_qs = Route.objects.filter(
        status='active', start_lat__isnull=False
    ).values('title', 'slug', 'start_lat', 'start_lng', 'difficulty', 'distance_km', 'duration_hours', 'avg_rating')

    categories = Category.objects.annotate(
        route_count=Count('routes', filter=Q(routes__status='active'))
    )

    return render(request, 'routes/list.html', {
        'routes': routes_page,
        'categories': categories,
        'map_routes_json': json.dumps(_serialize_routes_for_map(map_routes_qs), ensure_ascii=False, cls=DecimalEncoder),
        'query': query,
        'current_category': category,
        'current_difficulty': difficulty,
        'current_sort': sort,
        'total_count': paginator.count,
        'map_lat':  getattr(settings, 'MAP_DEFAULT_LAT', 49.8047),
        'map_lng':  getattr(settings, 'MAP_DEFAULT_LNG', 73.1094),
        'map_zoom': getattr(settings, 'MAP_DEFAULT_ZOOM', 11),
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

    # Points for map — serialize to JSON
    points_qs = route.points.all().order_by('order')
    points_list = []
    for p in points_qs:
        if p.lat is None or p.lng is None:
            continue
        points_list.append({
            'name':       p.name,
            'lat':        float(p.lat),
            'lng':        float(p.lng),
            'point_type': p.point_type if hasattr(p, 'point_type') else 'waypoint',
            'description': getattr(p, 'description', '') or '',
        })

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
    recommended = get_recommendations(
        request.user if request.user.is_authenticated else None, route, limit=4
    )

    return render(request, 'routes/detail.html', {
        'route': route,
        'points': points_qs,                         # для списка точек в шаблоне
        'points_json': json.dumps(points_list, ensure_ascii=False),  # для карты
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
                'rating':     review.rating,
                'comment':    review.comment,
                'user':       request.user.get_full_name() or request.user.username,
                'avatar':     request.user.avatar_url,
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
    from apps.places.models import Place

    routes_qs = Route.objects.filter(
        status='active', start_lat__isnull=False
    ).values(
        'title', 'slug', 'start_lat', 'start_lng',
        'difficulty', 'distance_km', 'duration_hours', 'avg_rating',
    )

    places_qs = Place.objects.filter(
        is_active=True, lat__isnull=False
    ).values('name', 'slug', 'lat', 'lng', 'category__name', 'category__icon', 'avg_rating')

    return render(request, 'routes/map.html', {
        'routes_json': json.dumps(
            _serialize_routes_for_map(routes_qs),
            ensure_ascii=False,
            cls=DecimalEncoder,
        ),
        'places_json': json.dumps(
            _serialize_places_for_map(places_qs),
            ensure_ascii=False,
            cls=DecimalEncoder,
        ),
        'map_lat':  getattr(settings, 'MAP_DEFAULT_LAT', 49.8047),
        'map_lng':  getattr(settings, 'MAP_DEFAULT_LNG', 73.1094),
        'map_zoom': getattr(settings, 'MAP_DEFAULT_ZOOM', 11),
    })


def route_geojson_api(request, slug):
    """API: Return GeoJSON for a specific route."""
    route = get_object_or_404(Route, slug=slug)
    points = list(route.points.order_by('order').values('lat', 'lng', 'name', 'point_type'))

    geojson = {'type': 'FeatureCollection', 'features': []}

    if route.route_geojson:
        geojson['features'].append({
            'type': 'Feature',
            'geometry': route.route_geojson,
            'properties': {'type': 'route', 'title': route.title, 'difficulty': route.difficulty},
        })
    elif len(points) >= 2:
        coords = [[p['lng'], p['lat']] for p in points if p['lat'] and p['lng']]
        if len(coords) >= 2:
            geojson['features'].append({
                'type': 'Feature',
                'geometry': {'type': 'LineString', 'coordinates': coords},
                'properties': {'type': 'route', 'title': route.title},
            })

    for point in points:
        if not point['lat'] or not point['lng']:
            continue
        geojson['features'].append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [float(point['lng']), float(point['lat'])]},
            'properties': {
                'type':       'waypoint',
                'name':       point['name'],
                'point_type': point['point_type'],
            },
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
                'type':        'Point',
                'coordinates': [float(route.start_lng), float(route.start_lat)],
            },
            'properties': {
                'id':               str(route.id),
                'title':            route.title,
                'slug':             route.slug,
                'difficulty':       route.difficulty,
                'difficulty_label': route.difficulty_label,
                'distance_km':      float(route.distance_km or 0),
                'duration_hours':   float(route.duration_hours or 0),
                'avg_rating':       float(route.avg_rating or 0) or None,
                'url':              route.get_absolute_url(),
            },
        })
    return JsonResponse({'type': 'FeatureCollection', 'features': features})


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)