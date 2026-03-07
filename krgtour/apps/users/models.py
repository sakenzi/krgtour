"""
Users app models - custom user model with profile.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with tourist profile fields."""

    email = models.EmailField(_('email address'), unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Tourist preferences
    preferred_difficulty = models.CharField(
        max_length=20,
        choices=[
            ('easy', 'Лёгкий'),
            ('medium', 'Средний'),
            ('hard', 'Сложный'),
            ('expert', 'Экстрим'),
        ],
        blank=True
    )
    interests = models.JSONField(default=list, blank=True)  # ['hiking', 'history', ...]

    # Stats
    total_routes_completed = models.PositiveIntegerField(default=0)
    total_km_traveled = models.FloatField(default=0.0)

    # Notifications
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def get_full_name(self):
        full = super().get_full_name()
        return full if full else self.username

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/images/default-avatar.svg'


class Notification(models.Model):
    """User notifications system."""

    TYPES = [
        ('booking_confirmed', 'Бронирование подтверждено'),
        ('booking_cancelled', 'Бронирование отменено'),
        ('review_reply', 'Ответ на отзыв'),
        ('new_route', 'Новый маршрут'),
        ('system', 'Системное'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.title}'