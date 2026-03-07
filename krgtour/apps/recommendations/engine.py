"""
Recommendation engine for tourist routes.

Logic:
1. Content-based filtering: recommend routes similar to what user has viewed/favorited
   - Same category
   - Similar difficulty
   - Similar distance

2. Collaborative filtering (simplified):
   - Find users with similar favorites
   - Recommend routes they liked but current user hasn't seen

3. Fallback: popular routes (highest booking_count + avg_rating)

The engine combines all signals with weighted scoring.
"""

from django.db.models import Q, Count
from django.core.cache import cache


def get_recommendations(user=None, current_route=None, limit=6):
    """
    Get recommended routes for a user.

    Args:
        user: Authenticated user or None for anonymous
        current_route: If on a route detail page, exclude it and use for context
        limit: Number of recommendations to return

    Returns:
        QuerySet of Route objects
    """
    from apps.routes.models import Route, Favorite, RouteView

    # Cache key
    user_id = user.id if user else 'anon'
    route_id = str(current_route.id) if current_route else 'none'
    cache_key = f'recommendations:{user_id}:{route_id}'

    cached = cache.get(cache_key)
    if cached:
        return cached

    base_qs = Route.objects.filter(status='active')
    if current_route:
        base_qs = base_qs.exclude(id=current_route.id)

    if user and user.is_authenticated:
        recommendations = _user_based_recommendations(user, current_route, base_qs, limit)
    else:
        recommendations = _popular_recommendations(current_route, base_qs, limit)

    # Cache for 10 minutes
    cache.set(cache_key, list(recommendations), 600)
    return recommendations


def _user_based_recommendations(user, current_route, base_qs, limit):
    """Personalized recommendations based on user history."""
    from apps.routes.models import Route, Favorite, RouteView

    # Get user's favorite route IDs
    fav_route_ids = list(
        Favorite.objects.filter(user=user).values_list('route_id', flat=True)
    )

    # Get user's viewed route IDs
    viewed_ids = list(
        RouteView.objects.filter(user=user).values_list('route_id', flat=True)
    )

    # Exclude already seen/favorited
    exclude_ids = set(fav_route_ids + viewed_ids)
    if current_route:
        exclude_ids.add(current_route.id)

    # Content-based: find similar routes
    candidates = base_qs.exclude(id__in=exclude_ids)

    # Get user's preferred categories from favorites
    if fav_route_ids:
        fav_routes = Route.objects.filter(id__in=fav_route_ids)
        fav_categories = list(fav_routes.values_list('category_id', flat=True).distinct())
        fav_difficulties = list(fav_routes.values_list('difficulty', flat=True))

        # Score by category match + difficulty match
        scored = []
        for route in candidates.select_related('category')[:50]:
            score = 0
            if route.category_id in fav_categories:
                score += 3
            if route.difficulty in fav_difficulties:
                score += 2
            score += route.avg_rating * 0.5
            score += min(route.booking_count / 10, 2)
            scored.append((score, route))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = [r for _, r in scored[:limit]]

        if len(result) >= limit:
            return result

    # Collaborative filtering: users with same favorites also liked...
    if fav_route_ids:
        similar_user_ids = list(
            Favorite.objects.filter(
                route_id__in=fav_route_ids
            ).exclude(
                user=user
            ).values_list('user_id', flat=True).distinct()[:50]
        )

        if similar_user_ids:
            collab_route_ids = list(
                Favorite.objects.filter(
                    user_id__in=similar_user_ids
                ).exclude(
                    route_id__in=exclude_ids
                ).values('route_id').annotate(
                    count=Count('id')
                ).order_by('-count').values_list('route_id', flat=True)[:limit]
            )

            collab_routes = list(base_qs.filter(id__in=collab_route_ids))
            if collab_routes:
                return collab_routes[:limit]

    # Fallback: popular
    return _popular_recommendations(current_route, candidates, limit)


def _popular_recommendations(current_route, base_qs, limit):
    """Fallback: popular routes by rating + bookings."""
    qs = base_qs

    # If we have a current route, prefer same category
    if current_route and current_route.category:
        same_cat = qs.filter(category=current_route.category).order_by('-avg_rating', '-booking_count')[:limit]
        if same_cat.count() >= limit // 2:
            return same_cat[:limit]

    return qs.order_by('-avg_rating', '-booking_count')[:limit]


def get_place_recommendations(user=None, current_place=None, limit=4):
    """Recommend places similar to current or based on user history."""
    from apps.places.models import Place, PlaceFavorite

    base_qs = Place.objects.filter(is_active=True)
    if current_place:
        base_qs = base_qs.exclude(id=current_place.id)

    if current_place and current_place.category:
        same_cat = base_qs.filter(
            category=current_place.category
        ).order_by('-avg_rating')[:limit]
        if same_cat.exists():
            return same_cat

    return base_qs.order_by('-avg_rating')[:limit]
