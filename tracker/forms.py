from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, FoodItem, MealEntry, WeightLog


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'gender',
            'age',
            'height',
            'activity_level',
            'deficit_rate',
            'current_weight',
            'target_weight',
            'calorie_target',
            'maintenance_calories',
            'protein_target',
            'carbs_target',
            'fat_target'
        ]
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 14, 'max': 110}),
            'height': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 240}),
            'activity_level': forms.TextInput(attrs={'class': 'form-control'}),
            'deficit_rate': forms.TextInput(attrs={'class': 'form-control'}),
            'calorie_target': forms.NumberInput(attrs={'class': 'form-control', 'min': 500, 'max': 10000}),
            'maintenance_calories': forms.NumberInput(attrs={'class': 'form-control', 'min': 500, 'max': 10000}),
            'protein_target': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 500}),
            'carbs_target': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 1000}),
            'fat_target': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 500}),
            'current_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 20, 'max': 300}),
            'target_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 20, 'max': 300}),
        }
        labels = {
            'calorie_target': 'Objetivo de Calorías Diarias (Déficit)',
            'maintenance_calories': 'Calorías de Mantenimiento Estimadas',
            'protein_target': 'Proteína Objetivo (g)',
            'carbs_target': 'Carbohidratos Objetivo (g)',
            'fat_target': 'Grasas Objetivo (g)',
            'current_weight': 'Peso Actual (kg)',
            'target_weight': 'Peso Meta (kg)',
        }


class FoodItemForm(forms.ModelForm):
    class Meta:
        model = FoodItem
        fields = [
            'name',
            'brand_or_notes',
            'serving_size',
            'calories',
            'protein',
            'carbs',
            'fat',
            'is_favorite'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Pechuga de pollo, Manzana, etc.'}),
            'brand_or_notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Sin piel, Marca X, etc.'}),
            'serving_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 1}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0}),
            'protein': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0}),
            'carbs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0}),
            'fat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0}),
            'is_favorite': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Nombre del alimento',
            'brand_or_notes': 'Marca o descripción (opcional)',
            'serving_size': 'Porción base (g o ml)',
            'calories': 'Calorías (kcal) por porción',
            'protein': 'Proteínas (g)',
            'carbs': 'Carbohidratos (g)',
            'fat': 'Grasas (g)',
            'is_favorite': 'Marcar como alimento habitual/favorito',
        }


class MealEntryForm(forms.ModelForm):
    class Meta:
        model = MealEntry
        fields = ['meal_type', 'food_item', 'grams_or_amount', 'date']
        widgets = {
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'food_item': forms.Select(attrs={'class': 'form-select select2-food'}),
            'grams_or_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '1', 'placeholder': 'Cantidad en gramos/ml'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'meal_type': 'Comida del día',
            'food_item': 'Alimento',
            'grams_or_amount': 'Cantidad consumida (g o ml)',
            'date': 'Fecha',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Show global foods + user's custom foods
            from django.db.models import Q
            self.fields['food_item'].queryset = FoodItem.objects.filter(
                Q(user__isnull=True) | Q(user=user)
            ).order_by('-is_favorite', 'name')


class WeightLogForm(forms.ModelForm):
    class Meta:
        model = WeightLog
        fields = ['date', 'weight', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 20, 'max': 300, 'placeholder': 'Ej. 78.5'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. En ayunas, post-entreno...'}),
        }
        labels = {
            'date': 'Fecha',
            'weight': 'Peso (kg)',
            'notes': 'Notas (opcional)',
        }


class RegisterForm(forms.Form):
    """Registro simple sin verificación ni restricciones complejas de contraseña."""
    username = forms.CharField(
        max_length=150,
        error_messages={'required': 'Ingresá un nombre de usuario.'},
    )
    password = forms.CharField(
        min_length=4,
        widget=forms.PasswordInput(),
        error_messages={
            'required': 'Ingresá una contraseña.',
            'min_length': 'La contraseña debe tener al menos 4 caracteres.',
        },
    )
    email = forms.EmailField(required=False)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError('Ingresá un nombre de usuario válido.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Ese nombre de usuario ya está registrado. Elegí otro.')
        return username

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=(self.cleaned_data.get('email') or '').strip(),
            password=self.cleaned_data['password'],
        )
        return user
