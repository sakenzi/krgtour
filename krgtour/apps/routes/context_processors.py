from .models import Category
from django.db.models import Count, Q


def categories_processor(request):
    """Make categories available in all templates."""
    categories = Category.objects.annotate(
        route_count=Count('routes', filter=Q(routes__status='active'))
    ).filter(route_count__gt=0)
    return {'nav_categories': categories}