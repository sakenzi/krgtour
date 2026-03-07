"""
Bookings app models - tour booking system.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class Booking(models.Model):
    """Tourist route booking."""

    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('refunded', 'Возвращено'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    route = models.ForeignKey('routes.Route', on_delete=models.CASCADE, related_name='bookings')

    # Booking details
    tour_date = models.DateField()
    num_people = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Contact info
    contact_name = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()

    # Notes
    special_requests = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Confirmation
    confirmation_code = models.CharField(max_length=20, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.confirmation_code} - {self.route.title} ({self.user.email})'

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            import random
            import string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            while Booking.objects.filter(confirmation_code=code).exists():
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.confirmation_code = code

        if not self.total_price and self.route.price:
            self.total_price = self.route.price * self.num_people

        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.tour_date >= timezone.now().date() and self.status in ['pending', 'confirmed']

    @property
    def can_cancel(self):
        from datetime import timedelta
        return (
            self.status in ['pending', 'confirmed'] and
            self.tour_date > (timezone.now().date() + timedelta(days=1))
        )