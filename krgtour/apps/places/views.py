"""
Places app views.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings

from .models import Place, PlaceCategory, PlaceReview, PlaceFavorite
from .forms import PlaceReviewForm


def place_list_view(request):
    places = Place.objects.filter(is_active=True).select_related('category')

    query = request.GET.get('q', '')
    if query:
        places = places.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    category = request.GET.get('category')
    if category:
        places = places.filter(category__slug=category)

    sort = request.GET.get('sort', '-created_at')
    sort_map = {'rating': '-avg_rating', 'name': 'name', 'new': '-created_at'}
    places = places.order_by(sort_map.get(sort, '-created_at'))

    paginator = Paginator(places, settings.PLACES_PER_PAGE)
    page = request.GET.get('page', 1)
    places_page = paginator.get_page(page)

    categories = PlaceCategory.objects.all()

    # Places for map
    map_places = list(Place.objects.filter(is_active=True, lat__isnull=False).values(
        'id', 'name', 'slug', 'lat', 'lng', 'category__name', 'category__icon', 'avg_rating'
    ))

    return render(request, 'places/list.html', {
        'places': places_page,
        'categories': categories,
        'map_places': map_places,
        'query': query,
        'current_category': category,
        'map_lat': settings.MAP_DEFAULT_LAT,
        'map_lng': settings.MAP_DEFAULT_LNG,
        'map_zoom': settings.MAP_DEFAULT_ZOOM,
    })


def place_detail_view(request, slug):
    place = get_object_or_404(Place, slug=slug, is_active=True)
    reviews = place.reviews.filter(is_approved=True).select_related('user')

    is_favorite = False
    user_review = None
    review_form = None
    if request.user.is_authenticated:
        is_favorite = PlaceFavorite.objects.filter(user=request.user, place=place).exists()
        user_review = PlaceReview.objects.filter(place=place, user=request.user).first()
        if not user_review:
            review_form = PlaceReviewForm()

    return render(request, 'places/detail.html', {
        'place': place,
        'reviews': reviews,
        'is_favorite': is_favorite,
        'user_review': user_review,
        'review_form': review_form,
        'nearby_routes': place.nearby_routes,
    })


@login_required
@require_POST
def toggle_place_favorite(request, slug):
    place = get_object_or_404(Place, slug=slug)
    favorite, created = PlaceFavorite.objects.get_or_create(user=request.user, place=place)
    if not created:
        favorite.delete()
        return JsonResponse({'success': True, 'is_favorite': False})
    return JsonResponse({'success': True, 'is_favorite': True})


@login_required
@require_POST
def add_place_review(request, slug):
    place = get_object_or_404(Place, slug=slug)
    if PlaceReview.objects.filter(place=place, user=request.user).exists():
        return JsonResponse({'success': False, 'error': 'Вы уже оставили отзыв.'})

    form = PlaceReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.place = place
        review.user = request.user
        review.save()
        # Update avg rating
        reviews = PlaceReview.objects.filter(place=place, is_approved=True)
        count = reviews.count()
        if count:
            avg = sum(r.rating for r in reviews) / count
            place.avg_rating = round(avg, 1)
            place.review_count = count
            place.save(update_fields=['avg_rating', 'review_count'])
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': form.errors})


def places_geojson_api(request):
    """GeoJSON for all places."""
    places = Place.objects.filter(is_active=True, lat__isnull=False)
    features = []
    for place in places:
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [place.lng, place.lat]},
            'properties': {
                'id': str(place.id),
                'name': place.name,
                'slug': place.slug,
                'category': place.category.name if place.category else '',
                'icon': place.category.icon if place.category else '📍',
                'avg_rating': place.avg_rating,
                'url': place.get_absolute_url(),
            }
        })
    return JsonResponse({'type': 'FeatureCollection', 'features': features})