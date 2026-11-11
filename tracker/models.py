from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    calorie_target = models.PositiveIntegerField(
        default=1800,
        help_text="Objetivo de calorías diarias para tu déficit"
    )
    protein_target = models.PositiveIntegerField(
        default=140,
        help_text="Objetivo de proteínas diarias (en gramos)"
    )
    carbs_target = models.PositiveIntegerField(
        default=160,
        help_text="Objetivo de carbohidratos diarios (en gramos)"
    )
    fat_target = models.PositiveIntegerField(
        default=55,
        help_text="Objetivo de grasas diarias (en gramos)"
    )
    maintenance_calories = models.PositiveIntegerField(
        default=2300,
        help_text="Calorías estimadas de mantenimiento"
    )
    current_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Peso actual en kg"
    )
    target_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Peso objetivo en kg"
    )
    onboarding_completed = models.BooleanField(
        default=False,
        help_text="Indica si el usuario completó el cuestionario inicial de déficit"
    )
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Hombre'), ('F', 'Mujer')],
        default='M',
        blank=True
    )
    age = models.PositiveIntegerField(null=True, blank=True, help_text="Edad en años")
    height = models.FloatField(null=True, blank=True, help_text="Altura en cm")
    activity_level = models.CharField(max_length=20, default='moderado', blank=True)
    deficit_rate = models.CharField(max_length=20, default='moderado', blank=True)
    passkey_user_handle = models.CharField(max_length=64, blank=True, default='', verbose_name="WebAuthn User Handle")

    def planned_deficit(self):
        """Déficit calórico planificado por día"""
        if self.maintenance_calories and self.calorie_target:
            return max(0, self.maintenance_calories - self.calorie_target)
        return 0

    def __str__(self):
        return f"Perfil de {self.user.username} (Meta: {self.calorie_target} kcal)"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()


class FoodItem(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_foods',
        help_text="Usuario creador. Vacío para catálogo general."
    )
    name = models.CharField(max_length=150, verbose_name="Nombre del alimento")
    brand_or_notes = models.CharField(max_length=150, blank=True, verbose_name="Marca o descripción")
    serving_size = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=Decimal('100.0'),
        verbose_name="Porción base (g o ml)",
        help_text="Generalmente 100g para facilitar cálculos"
    )
    calories = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        verbose_name="Calorías (kcal) por porción"
    )
    protein = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.0'),
        verbose_name="Proteínas (g)"
    )
    carbs = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.0'),
        verbose_name="Carbohidratos (g)"
    )
    fat = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.0'),
        verbose_name="Grasas (g)"
    )
    is_favorite = models.BooleanField(default=False, verbose_name="Favorito")
    photo = models.ImageField(upload_to='food_photos/', blank=True, null=True, verbose_name="Foto del alimento")
    photo_data = models.TextField(blank=True, default='', verbose_name="Foto persistente (base64 JPEG)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Alimento"
        verbose_name_plural = "Alimentos"

    def __str__(self):
        desc = f" ({self.brand_or_notes})" if self.brand_or_notes else ""
        return f"{self.name}{desc} - {self.calories} kcal / {self.serving_size}g"


class MealEntry(models.Model):
    MEAL_CHOICES = [
        ('desayuno', 'Desayuno'),
        ('almuerzo', 'Almuerzo'),
        ('merienda', 'Merienda'),
        ('cena', 'Cena'),
        ('snack', 'Snack / Colación'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_entries')
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    meal_type = models.CharField(max_length=20, choices=MEAL_CHOICES, default='almuerzo', verbose_name="Tipo de comida")
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, verbose_name="Alimento")
    grams_or_amount = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=Decimal('100.0'),
        verbose_name="Cantidad consumida (g/ml)"
    )
    photo = models.ImageField(upload_to='meal_photos/', blank=True, null=True, verbose_name="Foto de la comida")
    photo_data = models.TextField(blank=True, default='', verbose_name="Foto persistente (base64 JPEG)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'created_at']
        verbose_name = "Registro de comida"
        verbose_name_plural = "Registros de comidas"

    @property
    def factor(self):
        if self.food_item.serving_size and self.food_item.serving_size > 0:
            return self.grams_or_amount / self.food_item.serving_size
        return Decimal('1.0')

    @property
    def total_calories(self):
        return round(self.food_item.calories * self.factor, 1)

    @property
    def total_protein(self):
        return round(self.food_item.protein * self.factor, 1)

    @property
    def total_carbs(self):
        return round(self.food_item.carbs * self.factor, 1)

    @property
    def total_fat(self):
        return round(self.food_item.fat * self.factor, 1)

    def __str__(self):
        return f"{self.date} | {self.get_meal_type_display()} | {self.food_item.name} ({self.grams_or_amount}g)"


class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weight_logs')
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    weight = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Peso (kg)")
    notes = models.CharField(max_length=200, blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='unique_user_daily_weight')
        ]
        verbose_name = "Registro de peso"
        verbose_name_plural = "Registros de peso"

    def __str__(self):
        return f"{self.date} - {self.user.username}: {self.weight} kg"


class PasskeyCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passkeys')
    credential_id = models.CharField(max_length=512, unique=True, verbose_name="Credential ID (Base64URL)")
    public_key = models.TextField(verbose_name="Public Key (Base64URL)")
    sign_count = models.BigIntegerField(default=0, verbose_name="Contador de firmas")
    transports = models.JSONField(default=list, blank=True, verbose_name="Transportes")
    credential_device_type = models.CharField(max_length=32, default='singleDevice')
    credential_backed_up = models.BooleanField(default=False)
    aaguid = models.CharField(max_length=64, blank=True, default='')
    name = models.CharField(max_length=120, default='Huella / Passkey del dispositivo')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Passkey biométrica"
        verbose_name_plural = "Passkeys biométricas"

    def __str__(self):
        return f"{self.user.username} - {self.name}"
