from django.urls import path
from apps.consulting.views import nutrition_views as views

urlpatterns = [
    path('nutrition/', views.nutrition_view, name='nutrition_dashboard'),
    path('nutrition/schedule/', views.nutrition_schedule_view, name='nutrition_schedule'),
]
