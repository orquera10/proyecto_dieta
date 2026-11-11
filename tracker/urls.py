from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('meal/add/', views.add_meal_entry, name='add_meal_entry'),
    path('meal/delete/<int:pk>/', views.delete_meal_entry, name='delete_meal_entry'),
    path('meal/photo/<int:entry_id>/', views.meal_photo_view, name='meal_photo'),
    path('food/photo/<int:food_id>/', views.food_photo_view, name='food_photo'),
    path('foods/', views.food_list_view, name='food_list'),
    path('foods/add/', views.add_food_view, name='add_food'),
    path('foods/edit/<int:pk>/', views.edit_food_view, name='edit_food'),
    path('settings/', views.profile_settings_view, name='profile_settings'),
    path('weight/', views.weight_tracker_view, name='weight_tracker'),
    path('api/foods/search/', views.api_food_search, name='api_food_search'),
    path('api/meal/quick-add/', views.api_quick_add_meal, name='api_quick_add_meal'),
    path('api/ai/parse-meal/', views.ai_parse_meal_view, name='ai_parse_meal'),
    path('api/ai/estimate-food/', views.ai_estimate_food_view, name='ai_estimate_food'),
    path('api/ai/calculate-deficit/', views.ai_calculate_deficit_view, name='ai_calculate_deficit'),
    path('api/ai/suggest-meal/', views.ai_suggest_meal_view, name='ai_suggest_meal'),
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('.well-known/assetlinks.json', views.assetlinks_view, name='assetlinks'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
]
