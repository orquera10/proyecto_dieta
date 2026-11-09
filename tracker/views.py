import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from .models import UserProfile, FoodItem, MealEntry, WeightLog
from .forms import UserProfileForm, FoodItemForm, MealEntryForm, WeightLogForm, RegisterForm
from .gemini_service import parse_meal_with_gemini, estimate_food_nutrition_with_gemini, calculate_deficit_with_gemini


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"¡Bienvenido {user.username}! Tu cuenta ha sido creada.")
            return redirect('profile_settings')
    else:
        form = RegisterForm()
    return render(request, 'tracker/register.html', {'form': form})


@login_required
def dashboard_view(request):
    # Parse date parameter or default to today
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    prev_date = selected_date - datetime.timedelta(days=1)
    next_date = selected_date + datetime.timedelta(days=1)
    is_today = (selected_date == timezone.localdate())

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Fetch meal entries for date
    entries = MealEntry.objects.filter(
        user=request.user,
        date=selected_date
    ).select_related('food_item')

    # Group entries by meal type and calculate totals
    meal_categories = [
        ('desayuno', 'Desayuno', 'fa-coffee'),
        ('almuerzo', 'Almuerzo', 'fa-utensils'),
        ('merienda', 'Merienda', 'fa-cookie-bite'),
        ('cena', 'Cena', 'fa-moon'),
        ('snack', 'Snacks y Colaciones', 'fa-apple-alt'),
    ]

    meals_data = []
    total_calories = Decimal('0.0')
    total_protein = Decimal('0.0')
    total_carbs = Decimal('0.0')
    total_fat = Decimal('0.0')

    for code, label, icon in meal_categories:
        cat_entries = [e for e in entries if e.meal_type == code]
        subtotal_cal = sum((e.total_calories for e in cat_entries), Decimal('0.0'))
        subtotal_prot = sum((e.total_protein for e in cat_entries), Decimal('0.0'))
        subtotal_carbs = sum((e.total_carbs for e in cat_entries), Decimal('0.0'))
        subtotal_fat = sum((e.total_fat for e in cat_entries), Decimal('0.0'))

        total_calories += subtotal_cal
        total_protein += subtotal_prot
        total_carbs += subtotal_carbs
        total_fat += subtotal_fat

        meals_data.append({
            'code': code,
            'label': label,
            'icon': icon,
            'entries': cat_entries,
            'subtotal_cal': round(subtotal_cal, 1),
            'subtotal_prot': round(subtotal_prot, 1),
            'subtotal_carbs': round(subtotal_carbs, 1),
            'subtotal_fat': round(subtotal_fat, 1),
        })

    # Caloric deficit calculations
    calorie_target = profile.calorie_target or 1800
    maintenance_cal = profile.maintenance_calories or 2300
    deficit_target = max(0, maintenance_cal - calorie_target)
    
    # Calories remaining to reach deficit target
    remaining_calories = calorie_target - total_calories
    
    # Real deficit achieved today compared to maintenance
    actual_deficit = maintenance_cal - total_calories

    # Percentage consumed of target
    cal_percentage = min(100, int((total_calories / Decimal(str(calorie_target))) * 100)) if calorie_target > 0 else 0
    prot_percentage = min(100, int((total_protein / Decimal(str(profile.protein_target or 140))) * 100))
    carbs_percentage = min(100, int((total_carbs / Decimal(str(profile.carbs_target or 160))) * 100))
    fat_percentage = min(100, int((total_fat / Decimal(str(profile.fat_target or 55))) * 100))

    # Weight tracking for the day
    daily_weight = WeightLog.objects.filter(user=request.user, date=selected_date).first()
    recent_weights = WeightLog.objects.filter(user=request.user).order_by('-date')[:7]

    # Available foods for quick add modal
    available_foods = FoodItem.objects.filter(
        Q(user__isnull=True) | Q(user=request.user)
    ).order_by('-is_favorite', 'name')

    context = {
        'selected_date': selected_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'is_today': is_today,
        'profile': profile,
        'meals_data': meals_data,
        'total_calories': round(total_calories, 1),
        'total_protein': round(total_protein, 1),
        'total_carbs': round(total_carbs, 1),
        'total_fat': round(total_fat, 1),
        'remaining_calories': round(remaining_calories, 1),
        'actual_deficit': round(actual_deficit, 1),
        'deficit_target': deficit_target,
        'cal_percentage': cal_percentage,
        'prot_percentage': prot_percentage,
        'carbs_percentage': carbs_percentage,
        'fat_percentage': fat_percentage,
        'daily_weight': daily_weight,
        'recent_weights': recent_weights,
        'available_foods': available_foods,
    }
    return render(request, 'tracker/dashboard.html', context)


@login_required
def add_meal_entry(request):
    date_str = request.GET.get('date') or request.POST.get('date')
    meal_type = request.GET.get('meal_type') or request.POST.get('meal_type') or 'almuerzo'
    
    initial = {'meal_type': meal_type}
    if date_str:
        initial['date'] = date_str

    if request.method == 'POST':
        form = MealEntryForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, f"¡{entry.food_item.name} añadido a {entry.get_meal_type_display()}!")
            return redirect(f"/dashboard/?date={entry.date.strftime('%Y-%m-%d')}")
    else:
        form = MealEntryForm(initial=initial, user=request.user)

    return render(request, 'tracker/add_meal_entry.html', {'form': form, 'date_str': date_str})


@login_required
def delete_meal_entry(request, pk):
    entry = get_object_or_404(MealEntry, pk=pk, user=request.user)
    date_str = entry.date.strftime('%Y-%m-%d')
    if request.method == 'POST':
        entry.delete()
        messages.info(request, "Comida eliminada del registro.")
    return redirect(f"/dashboard/?date={date_str}")


@login_required
def food_list_view(request):
    q = request.GET.get('q', '').strip()
    foods = FoodItem.objects.filter(
        Q(user__isnull=True) | Q(user=request.user)
    )
    if q:
        foods = foods.filter(Q(name__icontains=q) | Q(brand_or_notes__icontains=q))

    foods = foods.order_by('-is_favorite', 'name')
    return render(request, 'tracker/food_list.html', {'foods': foods, 'q': q})


@login_required
def add_food_view(request):
    if request.method == 'POST':
        form = FoodItemForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.user = request.user
            food.save()
            messages.success(request, f"Alimento '{food.name}' creado exitosamente.")
            return redirect('food_list')
    else:
        form = FoodItemForm()
    return render(request, 'tracker/food_form.html', {'form': form, 'title': 'Nuevo Alimento'})


@login_required
def edit_food_view(request, pk):
    food = get_object_or_404(FoodItem, pk=pk, user=request.user)
    if request.method == 'POST':
        form = FoodItemForm(request.POST, instance=food)
        if form.is_valid():
            form.save()
            messages.success(request, f"Alimento '{food.name}' actualizado.")
            return redirect('food_list')
    else:
        form = FoodItemForm(instance=food)
    return render(request, 'tracker/food_form.html', {'form': form, 'title': f'Editar: {food.name}'})


@login_required
def profile_settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración de déficit calórico guardada correctamente.")
            return redirect('dashboard')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'tracker/profile_settings.html', {'form': form, 'profile': profile})


@login_required
def weight_tracker_view(request):
    if request.method == 'POST':
        form = WeightLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            # Update existing for that date or create
            WeightLog.objects.update_or_create(
                user=request.user,
                date=log.date,
                defaults={'weight': log.weight, 'notes': log.notes}
            )
            # Also update profile current_weight if date is today or recent
            profile = request.user.profile
            profile.current_weight = log.weight
            profile.save()
            messages.success(request, f"Peso de {log.weight} kg registrado para {log.date}.")
            return redirect('weight_tracker')
    else:
        today_log = WeightLog.objects.filter(user=request.user, date=timezone.localdate()).first()
        initial = {'date': timezone.localdate()}
        if today_log:
            initial['weight'] = today_log.weight
            initial['notes'] = today_log.notes
        form = WeightLogForm(initial=initial)

    logs = WeightLog.objects.filter(user=request.user).order_by('-date')
    return render(request, 'tracker/weight_tracker.html', {'form': form, 'logs': logs})


@login_required
def api_food_search(request):
    query = request.GET.get('q', '').strip()
    foods = FoodItem.objects.filter(
        Q(user__isnull=True) | Q(user=request.user)
    )
    if query:
        foods = foods.filter(Q(name__icontains=query) | Q(brand_or_notes__icontains=query))

    results = []
    for f in foods[:25]:
        results.append({
            'id': f.id,
            'name': f.name,
            'brand': f.brand_or_notes,
            'serving': float(f.serving_size),
            'calories': float(f.calories),
            'protein': float(f.protein),
            'carbs': float(f.carbs),
            'fat': float(f.fat),
        })
    return JsonResponse({'results': results})


@login_required
def ai_parse_meal_view(request):
    """Analiza una comida en lenguaje natural con Gemini 3.5 Flash Lite y opcionalmente la registra"""
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)

    import json
    try:
        if request.content_type == 'application/json':
            body = json.loads(request.body.decode('utf-8'))
        else:
            body = request.POST

        text = body.get('text', '').strip()
        date_str = body.get('date', '').strip()
        default_meal_type = body.get('meal_type', 'almuerzo')
        auto_save = body.get('auto_save', True)

        if not text:
            return JsonResponse({"error": "Por favor escribe lo que comiste para que la IA lo analice."}, status=400)

        # Parse date
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        # Call Gemini service
        res = parse_meal_with_gemini(text, default_meal_type=default_meal_type)
        if "error" in res:
            return JsonResponse({"error": res["error"]}, status=500)

        foods = res.get("foods", [])
        saved_entries = []

        if auto_save:
            for item in foods:
                name = item["name"]
                grams = Decimal(str(item["grams"]))
                cal = Decimal(str(item["calories"]))
                prot = Decimal(str(item["protein"]))
                carbs = Decimal(str(item["carbs"]))
                fat = Decimal(str(item["fat"]))
                item_meal_type = item.get("meal_type", default_meal_type)

                # Base per 100g calculation for the FoodItem reusable catalog
                factor_100 = (Decimal('100.0') / grams) if grams > 0 else Decimal('1.0')
                cal_100 = round(cal * factor_100, 1)
                prot_100 = round(prot * factor_100, 2)
                carbs_100 = round(carbs * factor_100, 2)
                fat_100 = round(fat * factor_100, 2)

                # Look for existing food or create a custom one for the user
                food_obj = FoodItem.objects.filter(
                    Q(user=request.user) | Q(user__isnull=True),
                    name__iexact=name
                ).first()

                if not food_obj:
                    food_obj = FoodItem.objects.create(
                        user=request.user,
                        name=name,
                        brand_or_notes="Generado por Gemini IA",
                        serving_size=Decimal('100.0'),
                        calories=cal_100,
                        protein=prot_100,
                        carbs=carbs_100,
                        fat=fat_100,
                        is_favorite=False
                    )

                # Create the meal entry
                entry = MealEntry.objects.create(
                    user=request.user,
                    date=target_date,
                    meal_type=item_meal_type,
                    food_item=food_obj,
                    grams_or_amount=grams
                )

                saved_entries.append({
                    "id": entry.id,
                    "name": food_obj.name,
                    "grams": float(grams),
                    "calories": float(entry.total_calories),
                    "protein": float(entry.total_protein),
                    "carbs": float(entry.total_carbs),
                    "fat": float(entry.total_fat),
                    "meal_type": entry.get_meal_type_display(),
                })

            messages.success(
                request,
                f"✨ Gemini registró {len(saved_entries)} alimentos: " +
                ", ".join(f"{e['name']} ({int(e['calories'])} kcal)" for e in saved_entries)
            )

        return JsonResponse({
            "success": True,
            "saved": auto_save,
            "count": len(foods),
            "foods": saved_entries if auto_save else foods,
            "date": target_date.strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.error(f"Error en ai_parse_meal_view: {e}")
        return JsonResponse({"error": f"Error inesperado: {str(e)}"}, status=500)


@login_required
def ai_estimate_food_view(request):
    """Estima los macros y porción de un alimento con Gemini 3.5 Flash Lite para autocompletar formularios"""
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)

    import json
    try:
        if request.content_type == 'application/json':
            body = json.loads(request.body.decode('utf-8'))
        else:
            body = request.POST

        query = body.get('query', '').strip()
        if not query:
            return JsonResponse({"error": "Por favor indica el nombre o descripción del alimento."}, status=400)

        res = estimate_food_nutrition_with_gemini(query)
        if "error" in res:
            return JsonResponse({"error": res["error"]}, status=500)

        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({"error": f"Error al procesar con IA: {str(e)}"}, status=500)


@login_required
def ai_calculate_deficit_view(request):
    """Calcula el TDEE, déficit y macros mediante un cuestionario interactivo con Gemini 3.5 Flash Lite"""
    if request.method != 'POST':
        return JsonResponse({"error": "Método no permitido"}, status=405)

    import json
    try:
        if request.content_type == 'application/json':
            body = json.loads(request.body.decode('utf-8'))
        else:
            body = request.POST

        data = {
            'gender': body.get('gender', 'M'),
            'age': int(body.get('age', 25) or 25),
            'height': float(body.get('height', 175) or 175),
            'current_weight': float(body.get('current_weight', 80) or 80),
            'target_weight': float(body.get('target_weight', 75) or 75),
            'activity_level': body.get('activity_level', 'moderado'),
            'deficit_rate': body.get('deficit_rate', 'moderado'),
            'notes': body.get('notes', '').strip(),
        }

        apply_to_profile = body.get('apply_to_profile', False)
        if isinstance(apply_to_profile, str):
            apply_to_profile = apply_to_profile.lower() in ('true', '1', 'yes')

        res = calculate_deficit_with_gemini(data)
        if "error" in res:
            return JsonResponse({"error": res["error"]}, status=500)

        if apply_to_profile and res.get('success'):
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if 'maintenance_calories' in res:
                profile.maintenance_calories = int(res['maintenance_calories'])
            if 'daily_calorie_target' in res:
                profile.calorie_target = int(res['daily_calorie_target'])
            if 'protein_target_g' in res:
                profile.protein_target = int(res['protein_target_g'])
            if 'carbs_target_g' in res:
                profile.carbs_target = int(res['carbs_target_g'])
            if 'fat_target_g' in res:
                profile.fat_target = int(res['fat_target_g'])
            if data['current_weight'] > 0:
                profile.current_weight = Decimal(str(data['current_weight']))
            if data['target_weight'] > 0:
                profile.target_weight = Decimal(str(data['target_weight']))
            profile.save()

            # Record weight log for today
            today = timezone.localdate()
            WeightLog.objects.update_or_create(
                user=request.user,
                date=today,
                defaults={'weight': Decimal(str(data['current_weight'])), 'notes': 'Calculado con Asistente IA'}
            )

            messages.success(request, f"🎯 ¡Metas actualizadas con IA! Nuevo objetivo: {res['daily_calorie_target']} kcal/día.")

        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({"error": f"Error: {str(e)}"}, status=500)


def manifest_view(request):
    """PWA Web App Manifest for mobile installation"""
    data = {
        "name": "Déficit Calórico Tracker",
        "short_name": "Déficit",
        "start_url": "/dashboard/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/3050/3050158.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "https://cdn-icons-png.flaticon.com/512/3050/3050158.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(data)

