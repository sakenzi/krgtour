from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.assistant_view, name='chat'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/suggest/', views.suggest_routes_api, name='suggest_api'),
    path('api/plan/', views.travel_plan_api, name='plan_api'),
]