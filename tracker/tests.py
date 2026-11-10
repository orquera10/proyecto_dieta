import json
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
        self.profile.onboarding_completed = True
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
        self.assertContains(response, 'Tu día, en balance')

    def test_deficit_calculation(self):
        self.assertEqual(self.profile.planned_deficit(), 500)

    def test_ai_parse_endpoint_validation(self):
        self.client.login(username='dario_test', password='TestPassword123')
        # Empty text should return 400
        response = self.client.post(
            reverse('ai_parse_meal'),
            data={'text': ''}
        )
        self.assertEqual(response.status_code, 400)

    def test_ai_parse_endpoint_with_text(self):
        self.client.login(username='dario_test', password='TestPassword123')
        response = self.client.post(
            reverse('ai_parse_meal'),
            data={'text': 'como 3 albondigas con una porcion de pure', 'auto_save': 'true'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['saved'])
        self.assertGreater(data['count'], 0)

    def test_ai_parse_endpoint_with_image_and_text(self):
        import base64
        self.client.login(username='dario_test', password='TestPassword123')
        # Tiny 1x1 transparent PNG in base64
        tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        response = self.client.post(
            reverse('ai_parse_meal'),
            data=json.dumps({
                'text': 'Plato de almuerzo saludable',
                'image_b64': tiny_png,
                'image_mime_type': 'image/png',
                'auto_save': True
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_ai_estimate_food_endpoint(self):
        self.client.login(username='dario_test', password='TestPassword123')
        response = self.client.post(
            reverse('ai_estimate_food'),
            data={'query': 'milanesa de pollo con papas al horno'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('calories', data)
        self.assertIn('protein', data)

    def test_ai_calculate_deficit_endpoint(self):
        self.client.login(username='dario_test', password='TestPassword123')
        response = self.client.post(
            reverse('ai_calculate_deficit'),
            data={
                'gender': 'M',
                'age': 30,
                'height': 178,
                'current_weight': 85,
                'target_weight': 77,
                'activity_level': 'moderado',
                'deficit_rate': 'moderado',
                'apply_to_profile': 'true'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('maintenance_calories', data)
        self.assertIn('daily_calorie_target', data)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.calorie_target, int(data['daily_calorie_target']))

    def test_onboarding_redirect_and_completion(self):
        new_user = User.objects.create_user(username='new_member', password='SecretPassword123')
        self.client.login(username='new_member', password='SecretPassword123')
        # Dashboard must redirect to onboarding
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse('onboarding'), res.headers.get('Location'))

        # Complete onboarding
        post_res = self.client.post(
            reverse('onboarding'),
            data=json.dumps({
                'gender': 'M',
                'age': 25,
                'height': 180,
                'weight': 82.5,
                'target': 76.0,
                'activity': 'moderado',
                'deficit_rate': 'equilibrado',
                'calorie_target': 1850,
                'protein_target': 148,
                'carbs_target': 180,
                'fat_target': 55,
                'maintenance_calories': 2350
            }),
            content_type='application/json'
        )
        self.assertEqual(post_res.status_code, 200)
        new_user.profile.refresh_from_db()
        self.assertTrue(new_user.profile.onboarding_completed)
        self.assertEqual(new_user.profile.calorie_target, 1850)

        # Now dashboard should return 200
        dash_res = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_res.status_code, 200)
