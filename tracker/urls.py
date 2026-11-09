from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('meal/add/', views.add_meal_entry, name='add_meal_entry'),
    path('meal/delete/<int:pk>/', views.delete_meal_entry, name='delete_meal_entry'),
    path('foods/', views.food_list_view, name='food_list'),
    path('foods/add/', views.add_food_view, name='add_food'),
    path('foods/edit/<int:pk>/', views.edit_food_view, name='edit_food'),
    path('settings/', views.profile_settings_view, name='profile_settings'),
    path('weight/', views.weight_tracker_view, name='weight_tracker'),
    path('api/foods/search/', views.api_food_search, name='api_food_search'),
    path('manifest.json', views.manifest_view, name='manifest'),
    
    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
]
