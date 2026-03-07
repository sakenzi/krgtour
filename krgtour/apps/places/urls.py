from django.urls import path
from . import views

app_name = 'places'

urlpatterns = [
    path('', views.place_list_view, name='list'),
    path('<slug:slug>/', views.place_detail_view, name='detail'),
    path('<slug:slug>/favorite/', views.toggle_place_favorite, name='toggle_favorite'),
    path('<slug:slug>/review/', views.add_place_review, name='add_review'),
    path('api/geojson/', views.places_geojson_api, name='geojson'),
]