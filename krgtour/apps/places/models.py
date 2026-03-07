"""
Places app models - points of interest on the map.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class PlaceCategory(models.Model):
    """Categories for places (museum, park, restaurant, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10, default='📍')
    color = models.CharField(max_length=7, default='#7C3AED')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Категория мест'
        verbose_name_plural = 'Категории мест'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Place(models.Model):
    """Point of interest / tourist place."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    cover_image = models.ImageField(upload_to='places/covers/', null=True, blank=True)
    category = models.ForeignKey(PlaceCategory, on_delete=models.SET_NULL, null=True, related_name='places')

    # Location
    lat = models.FloatField()
    lng = models.FloatField()
    address = models.CharField(max_length=300, blank=True)

    # Info
    working_hours = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    entry_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Ratings
    avg_rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Место'
        verbose_name_plural = 'Места'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            if not base_slug:
                base_slug = str(self.id)[:8]
            self.slug = base_slug
            counter = 1
            while Place.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('places:detail', kwargs={'slug': self.slug})

    @property
    def nearby_routes(self):
        """Get routes that pass near this place."""
        from apps.routes.models import RoutePoint
        route_ids = RoutePoint.objects.filter(place=self).values_list('route_id', flat=True)
        from apps.routes.models import Route
        return Route.objects.filter(id__in=route_ids, status='active')[:5]


class PlaceImage(models.Model):
    """Gallery images for places."""
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='places/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']


class PlaceReview(models.Model):
    """Reviews for places."""
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['place', 'user']
        ordering = ['-created_at']


class PlaceFavorite(models.Model):
    """User favorite places."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='place_favorites')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'place']