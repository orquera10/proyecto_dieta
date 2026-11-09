from django.contrib import admin
from .models import UserProfile, FoodItem, MealEntry, WeightLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'calorie_target', 'protein_target', 'carbs_target', 'fat_target', 'current_weight', 'target_weight')
    search_fields = ('user__username', 'user__email')


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand_or_notes', 'serving_size', 'calories', 'protein', 'carbs', 'fat', 'is_favorite', 'user')
    list_filter = ('is_favorite', 'user')
    search_fields = ('name', 'brand_or_notes')


@admin.register(MealEntry)
class MealEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'meal_type', 'food_item', 'grams_or_amount', 'total_calories', 'total_protein')
    list_filter = ('meal_type', 'date', 'user')
    search_fields = ('food_item__name', 'user__username')


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight', 'notes')
    list_filter = ('date', 'user')
    search_fields = ('user__username', 'notes')
