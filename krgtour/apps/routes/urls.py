from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('routes/', views.route_list_view, name='list'),
    path('routes/<slug:slug>/', views.route_detail_view, name='detail'),
    path('routes/<slug:slug>/review/', views.add_review_view, name='add_review'),
    path('routes/<slug:slug>/favorite/', views.toggle_favorite_view, name='toggle_favorite'),
    path('routes/<slug:slug>/geojson/', views.route_geojson_api, name='geojson'),
    path('map/', views.map_view, name='map'),
    path('api/routes/geojson/', views.all_routes_geojson_api, name='all_geojson'),
]