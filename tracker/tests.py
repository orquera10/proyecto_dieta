from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import FoodItem, MealEntry, UserProfile, WeightLog


class DeficitTrackerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dario_test', password='TestPassword123')
        self.profile = self.user.profile
        self.profile.calorie_target = 1800
        self.profile.maintenance_calories = 2300
        self.profile.save()

        self.chicken = FoodItem.objects.create(
            name='Pechuga de Pollo',
            serving_size=Decimal('100.0'),
            calories=Decimal('165.0'),
            protein=Decimal('31.0'),
            carbs=Decimal('0.0'),
            fat=Decimal('3.6')
        )

    def test_meal_entry_calculations(self):
        # 200g of chicken should be 2x serving size
        entry = MealEntry.objects.create(
            user=self.user,
            meal_type='almuerzo',
            food_item=self.chicken,
            grams_or_amount=Decimal('200.0')
        )
        self.assertEqual(entry.total_calories, Decimal('330.0'))
        self.assertEqual(entry.total_protein, Decimal('62.0'))
        self.assertEqual(entry.total_fat, Decimal('7.2'))

    def test_dashboard_authenticated(self):
        self.client.login(username='dario_test', password='TestPassword123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Balance Calórico Diario')

    def test_deficit_calculation(self):
        self.assertEqual(self.profile.planned_deficit(), 500)
