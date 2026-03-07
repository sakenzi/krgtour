"""
Main URL configuration for Karaganda Tourist Routes.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Django admin (default)
    path('django-admin/', admin.site.urls),

    # Main routes app (homepage)
    path('', include('apps.routes.urls', namespace='routes')),

    # Places
    path('places/', include('apps.places.urls', namespace='places')),

    # Bookings
    path('bookings/', include('apps.bookings.urls', namespace='bookings')),

    # Users (auth + profiles)
    path('users/', include('apps.users.urls', namespace='users')),

    # AI Assistant
    path('ai/', include('apps.ai_assistant.urls', namespace='ai_assistant')),

    # Custom Admin Dashboard
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler404 = 'apps.routes.views.handler404'
handler500 = 'apps.routes.views.handler500'