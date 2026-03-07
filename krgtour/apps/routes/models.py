"""
Routes app models - the core of the tourist routes system.
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Category(models.Model):
    """Route categories (hiking, history, nature, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class or emoji')
    color = models.CharField(max_length=7, default='#7C3AED')
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Route(models.Model):
    """Main tourist route model."""

    DIFFICULTY_CHOICES = [
        ('easy', 'Лёгкий'),
        ('medium', 'Средний'),
        ('hard', 'Сложный'),
        ('expert', 'Экстрим'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активный'),
        ('archived', 'Архив'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    cover_image = models.ImageField(upload_to='routes/covers/')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='routes')

    # Route characteristics
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    distance_km = models.FloatField(validators=[MinValueValidator(0.1)])
    duration_hours = models.FloatField(validators=[MinValueValidator(0.5)])
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_group_size = models.PositiveIntegerField(default=20)
    min_age = models.PositiveIntegerField(default=0)

    # Geographic data
    start_lat = models.FloatField(null=True, blank=True)
    start_lng = models.FloatField(null=True, blank=True)
    end_lat = models.FloatField(null=True, blank=True)
    end_lng = models.FloatField(null=True, blank=True)
    route_geojson = models.JSONField(null=True, blank=True, help_text='GeoJSON LineString for route path')

    # Meta
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_routes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Computed/cached fields
    avg_rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    booking_count = models.PositiveIntegerField(default=0)

    # Tags
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = 'Маршрут'
        verbose_name_plural = 'Маршруты'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            if not base_slug:
                base_slug = str(self.id)[:8]
            self.slug = base_slug
            # Ensure uniqueness
            counter = 1
            while Route.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('routes:detail', kwargs={'slug': self.slug})

    @property
    def difficulty_color(self):
        colors = {
            'easy': '#10B981',
            'medium': '#F59E0B',
            'hard': '#EF4444',
            'expert': '#7C3AED',
        }
        return colors.get(self.difficulty, '#6B7280')

    @property
    def difficulty_label(self):
        return dict(self.DIFFICULTY_CHOICES).get(self.difficulty, '')

    @property
    def price_display(self):
        if self.price:
            return f'{int(self.price):,} ₸'
        return 'Бесплатно'

    def update_rating(self):
        from apps.routes.models import Review
        reviews = Review.objects.filter(route=self, is_approved=True)
        count = reviews.count()
        if count > 0:
            avg = sum(r.rating for r in reviews) / count
            self.avg_rating = round(avg, 1)
            self.review_count = count
            self.save(update_fields=['avg_rating', 'review_count'])


class RoutePoint(models.Model):
    """Individual points along a route."""

    POINT_TYPES = [
        ('start', 'Старт'),
        ('waypoint', 'Промежуточная точка'),
        ('attraction', 'Достопримечательность'),
        ('rest', 'Место отдыха'),
        ('end', 'Финиш'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='points')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    order = models.PositiveIntegerField(default=0)
    point_type = models.CharField(max_length=20, choices=POINT_TYPES, default='waypoint')
    image = models.ImageField(upload_to='routes/points/', null=True, blank=True)
    place = models.ForeignKey(
        'places.Place',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='route_points'
    )

    class Meta:
        verbose_name = 'Точка маршрута'
        verbose_name_plural = 'Точки маршрута'
        ordering = ['order']

    def __str__(self):
        return f'{self.route.title} - {self.name}'


class RouteImage(models.Model):
    """Gallery images for routes."""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='routes/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image for {self.route.title}'


class Review(models.Model):
    """User reviews and ratings for routes."""

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    visit_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = ['route', 'user']

    def __str__(self):
        return f'{self.user.username} - {self.route.title} ({self.rating}★)'


class Favorite(models.Model):
    """User favorite routes."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='route_favorites')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'route']
        verbose_name = 'Избранный маршрут'
        verbose_name_plural = 'Избранные маршруты'


class RouteView(models.Model):
    """Track route views for recommendations."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='views_log')
    session_key = models.CharField(max_length=40, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Просмотр маршрута'