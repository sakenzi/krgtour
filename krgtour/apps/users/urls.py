from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/password/', views.change_password_view, name='change_password'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('bookings/', views.bookings_history_view, name='bookings_history'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/count/', views.notifications_count_api, name='notifications_count'),
    path('<str:username>/', views.public_profile_view, name='public_profile'),
]