from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('create/<slug:route_slug>/', views.create_booking_view, name='create'),
    path('<uuid:pk>/', views.booking_detail_view, name='detail'),
    path('<uuid:pk>/cancel/', views.cancel_booking_view, name='cancel'),
    path('api/price/', views.calculate_price_api, name='price_api'),
]