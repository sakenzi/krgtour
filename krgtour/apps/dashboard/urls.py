from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('routes/', views.route_list_dashboard, name='route_list'),
    path('routes/create/', views.route_create_dashboard, name='route_create'),
    path('routes/<slug:slug>/edit/', views.route_edit_dashboard, name='route_edit'),
    path('routes/<slug:slug>/delete/', views.route_delete_dashboard, name='route_delete'),
    path('routes/<slug:slug>/upload/', views.upload_route_image, name='upload_image'),
    path('bookings/', views.bookings_dashboard, name='bookings'),
    path('bookings/<uuid:pk>/status/', views.update_booking_status, name='booking_status'),
    path('reviews/', views.reviews_dashboard, name='reviews'),
    path('reviews/<int:pk>/moderate/', views.moderate_review, name='review_moderate'),
]