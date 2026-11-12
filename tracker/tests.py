import os
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
        self.assertEqual(float(new_user.profile.current_weight), 82.5)
        self.assertEqual(float(new_user.profile.target_weight), 76.0)

        # Profile settings must render dot-decimal values for HTML5 number inputs
        prof_res = self.client.get(reverse('profile_settings'))
        self.assertEqual(prof_res.status_code, 200)
        self.assertContains(prof_res, 'value="82.5"')
        self.assertContains(prof_res, 'value="76.0"')

        # Now dashboard should return 200
        dash_res = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_res.status_code, 200)

    def test_ai_suggest_meal_endpoint(self):
        self.client.login(username='dario_test', password='TestPassword123')
        response = self.client.post(
            reverse('ai_suggest_meal'),
            data=json.dumps({
                'query': '¿Qué puedo cenar liviano para completar mis calorías?',
                'meal_type': 'cena'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('advice', data)
        self.assertIn('suggestions', data)
        self.assertTrue(len(data['suggestions']) > 0)
        self.assertIn('remaining_calories', data)

    def test_ai_suggest_meal_detects_pending_cena(self):
        from .models import FoodItem, MealEntry
        from django.utils import timezone

        today = timezone.localdate()
        f1 = FoodItem.objects.create(user=self.user, name='Café con leche y tostadas', calories=320, protein=14, carbs=40, fat=10, serving_size=100)
        f2 = FoodItem.objects.create(user=self.user, name='Pollo con ensalada', calories=520, protein=45, carbs=25, fat=18, serving_size=100)
        f3 = FoodItem.objects.create(user=self.user, name='Yogur con fruta', calories=210, protein=12, carbs=28, fat=4, serving_size=100)

        MealEntry.objects.create(user=self.user, date=today, meal_type='desayuno', food_item=f1, grams_or_amount=100)
        MealEntry.objects.create(user=self.user, date=today, meal_type='almuerzo', food_item=f2, grams_or_amount=100)
        MealEntry.objects.create(user=self.user, date=today, meal_type='merienda', food_item=f3, grams_or_amount=100)

        self.client.login(username='dario_test', password='TestPassword123')
        dash_res = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertEqual(dash_res.context['pending_meal_code'], 'cena')

        response = self.client.post(
            reverse('ai_suggest_meal'),
            data=json.dumps({
                'query': '¿Qué me recomendás comer para completar el día según mis calorías restantes?',
                'meal_type': 'almuerzo',
                'user_explicit_meal': False,
                'date': today.strftime('%Y-%m-%d'),
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['recommended_meal_type'], 'cena')

    def test_persistent_photo_served_after_disk_deletion(self):
        import io
        import base64
        from PIL import Image
        from unittest.mock import patch
        from .models import MealEntry
        from django.utils import timezone

        # Generate valid in-memory PNG image
        img = Image.new('RGB', (60, 60), color=(200, 90, 40))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64_img = base64.b64encode(buf.getvalue()).decode('ascii')

        mock_gemini_resp = {
            "meal_type": "almuerzo",
            "foods": [{
                "name": "Bowl de pollo test",
                "grams": 250,
                "calories": 420,
                "protein": 38,
                "carbs": 35,
                "fat": 12
            }]
        }

        self.client.login(username='dario_test', password='TestPassword123')
        with patch('tracker.views.parse_meal_with_gemini', return_value=mock_gemini_resp):
            resp = self.client.post(
                reverse('ai_parse_meal'),
                data=json.dumps({
                    'image_b64': b64_img,
                    'image_mime_type': 'image/png',
                    'meal_type': 'almuerzo',
                    'auto_save': True,
                    'date': timezone.localdate().strftime('%Y-%m-%d'),
                }),
                content_type='application/json'
            )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

        entry = MealEntry.objects.filter(user=self.user, meal_type='almuerzo').latest('id')
        self.assertTrue(bool(entry.photo_data))

        # Simulate Coolify redeploy wiping ephemeral MEDIA_ROOT file
        if entry.photo and os.path.exists(entry.photo.path):
            os.remove(entry.photo.path)

        photo_url = reverse('meal_photo', args=[entry.id])
        photo_res = self.client.get(photo_url)
        self.assertEqual(photo_res.status_code, 200)
        self.assertEqual(photo_res['Content-Type'], 'image/jpeg')
        self.assertTrue(len(photo_res.content) > 100)

        # Dashboard must still link to the persistent photo URL instead of Unsplash fallback
        dash_res = self.client.get(reverse('dashboard'))
        self.assertContains(dash_res, photo_url)


class PolishAndPasskeyTests(TestCase):
    """Tests for NÜTRA auth styling, native dialog modal semantics, and WebAuthn endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(username='biouser', password='password123')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.onboarding_completed = True
        self.profile.save(update_fields=['onboarding_completed'])

    def test_login_and_register_nutra_ui(self):
        login_res = self.client.get(reverse('login'))
        self.assertEqual(login_res.status_code, 200)
        self.assertContains(login_res, 'Volvé a tu balance.')
        self.assertContains(login_res, 'Nutri<span')
        self.assertContains(login_res, 'autocomplete="username webauthn"')
        self.assertContains(login_res, 'id="btnPasskeySignIn"')
        self.assertNotContains(login_res, 'class="glass-nav"')

        register_res = self.client.get(reverse('register'))
        self.assertEqual(register_res.status_code, 200)
        self.assertContains(register_res, 'Creá tu cuenta.')
        self.assertContains(register_res, 'NutriX')
        self.assertNotContains(register_res, 'class="glass-nav"')

        manifest_res = self.client.get(reverse('manifest'))
        self.assertEqual(manifest_res.status_code, 200)
        manifest_data = manifest_res.json()
        self.assertEqual(manifest_data['short_name'], 'NutriX')
        self.assertEqual(manifest_data['name'], 'NutriX')

    def test_dashboard_native_dialogs_and_no_legacy_backdrop(self):
        self.client.login(username='biouser', password='password123')
        dash_res = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, 'class="nutrix-week-strip"')
        self.assertContains(dash_res, '<dialog class="nutra-bottom-sheet" id="assistantSheet" closedby="any"')
        self.assertContains(dash_res, '<dialog id="cameraViewfinderModal"')
        self.assertNotContains(dash_res, 'id="sheetBackdrop"')

    def test_passkey_options_and_unknown_credential_404(self):
        # Public auth options should succeed unauthenticated with discoverable allowCredentials=[]
        auth_opt_res = self.client.post(
            reverse('passkey_auth_options'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(auth_opt_res.status_code, 200)
        auth_payload = auth_opt_res.json()
        self.assertIn('challenge', auth_payload)
        self.assertIn('rpId', auth_payload)
        self.assertEqual(auth_payload.get('allowCredentials'), [])

        # Unknown credential verification MUST return HTTP 404 for signalUnknownCredential
        unknown_verify_res = self.client.post(
            reverse('passkey_auth_verify'),
            data=json.dumps({'id': 'nonexistent-credential-id-xyz', 'rawId': 'nonexistent-credential-id-xyz'}),
            content_type='application/json',
        )
        self.assertEqual(unknown_verify_res.status_code, 404)

        # Authenticated registration options should include user handle, rp.id, and preferred UV
        self.client.login(username='biouser', password='password123')
        reg_opt_res = self.client.post(
            reverse('passkey_register_options'),
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(reg_opt_res.status_code, 200)
        reg_payload = reg_opt_res.json()
        self.assertIn('challenge', reg_payload)
        self.assertIn('rp', reg_payload)
        self.assertIn('id', reg_payload['rp'])
        self.assertIn('user', reg_payload)
        self.assertIn('authenticatorSelection', reg_payload)
        self.assertEqual(reg_payload['authenticatorSelection'].get('userVerification'), 'preferred')

    def test_dashboard_date_navigation_and_history(self):
        from django.utils import timezone
        import datetime

        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        food = FoodItem.objects.create(
            name='Salmón histórico',
            calories=Decimal('210.0'),
            protein=Decimal('22.0'),
            carbs=Decimal('0.0'),
            fat=Decimal('12.0'),
        )
        MealEntry.objects.create(
            user=self.user,
            food_item=food,
            meal_type='cena',
            date=yesterday,
            grams_or_amount=Decimal('150.0'),
        )
        self.client.login(username='biouser', password='password123')
        today_res = self.client.get(reverse('dashboard'))
        self.assertContains(today_res, f'?date={yesterday.strftime("%Y-%m-%d")}')
        self.assertContains(today_res, 'id="dashboardDatePicker"')

        past_res = self.client.get(reverse('dashboard') + f'?date={yesterday.strftime("%Y-%m-%d")}')
        self.assertEqual(past_res.status_code, 200)
        self.assertContains(past_res, 'Salmón histórico')
        self.assertContains(past_res, 'Volver a hoy')
        self.assertContains(past_res, 'id="btnClearDayMeals"')
        self.assertContains(past_res, 'id="nutraSystemDialog"')

        # Empty today should not render btnClearDayMeals
        self.assertNotContains(today_res, 'id="btnClearDayMeals"')

        # Also add an entry today to make sure deleting yesterday doesn't delete today
        MealEntry.objects.create(
            user=self.user,
            food_item=food,
            meal_type='almuerzo',
            date=timezone.localdate(),
            grams_or_amount=Decimal('100.0'),
        )
        del_res = self.client.post(reverse('delete_day_entries', args=[yesterday.strftime('%Y-%m-%d')]))
        self.assertEqual(del_res.status_code, 302)
        self.assertEqual(MealEntry.objects.filter(user=self.user, date=yesterday).count(), 0)
        self.assertEqual(MealEntry.objects.filter(user=self.user, date=timezone.localdate()).count(), 1)

    def test_simple_registration_without_verification(self):
        # Simple 4-char password and blank email should immediately create user & redirect to onboarding
        res = self.client.post(reverse('register'), data={
            'username': 'nuevo123',
            'password': '1234',
            'email': '',
        })
        self.assertRedirects(res, reverse('onboarding'), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username='nuevo123').exists())
        # User should already be logged in
        onb_res = self.client.get(reverse('onboarding'))
        self.assertEqual(onb_res.status_code, 200)

        # Duplicate username (case-insensitive) should fail with friendly Spanish message
        self.client.logout()
        dup_res = self.client.post(reverse('register'), data={
            'username': 'NUEVO123',
            'password': '1234',
        })
        self.assertEqual(dup_res.status_code, 200)
        self.assertContains(dup_res, 'Ese nombre de usuario ya está registrado')

    def test_modal_round_close_and_top_ia_button(self):
        self.client.login(username='biouser', password='password123')
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode('utf-8')

        # Check round close class is used
        self.assertIn('class="nutra-modal-close"', html)
        self.assertNotIn('class="btn-close"', html)

        # Check 'Prefiero registrarlo con IA' is at the top of quickAddSheet (before search input)
        idx_quick_add = html.find('id="quickAddSheet"')
        self.assertNotEqual(idx_quick_add, -1)
        idx_ia_btn = html.find('Prefiero registrarlo con IA', idx_quick_add)
        idx_search_input = html.find('id="quickFoodSearchInput"', idx_quick_add)

        self.assertNotEqual(idx_ia_btn, -1)
        self.assertNotEqual(idx_search_input, -1)
        self.assertLess(idx_ia_btn, idx_search_input, "IA button must be located above the food search input in quickAddSheet")





