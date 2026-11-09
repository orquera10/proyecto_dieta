from django.core.management.base import BaseCommand
from decimal import Decimal
from tracker.models import FoodItem

SAMPLE_FOODS = [
    # Proteínas
    {"name": "Pechuga de Pollo a la plancha", "brand_or_notes": "Cocida sin piel", "serving_size": 100, "calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
    {"name": "Huevo Entero", "brand_or_notes": "Unidad grande (~50g)", "serving_size": 50, "calories": 72, "protein": 6.3, "carbs": 0.4, "fat": 4.8},
    {"name": "Clara de Huevo", "brand_or_notes": "100g de claras líquidas", "serving_size": 100, "calories": 52, "protein": 11.0, "carbs": 0.7, "fat": 0.2},
    {"name": "Atún al natural", "brand_or_notes": "Lata escurrida", "serving_size": 100, "calories": 116, "protein": 26.0, "carbs": 0.0, "fat": 1.0},
    {"name": "Carne magra vacuna (Lomo/Cuadril)", "brand_or_notes": "Cocida", "serving_size": 100, "calories": 180, "protein": 28.0, "carbs": 0.0, "fat": 7.0},
    {"name": "Yogur Griego Descremado / Natural", "brand_or_notes": "Alto en proteína", "serving_size": 100, "calories": 59, "protein": 10.0, "carbs": 3.6, "fat": 0.4},
    {"name": "Proteína Whey (Suero)", "brand_or_notes": "1 scoop (~30g)", "serving_size": 30, "calories": 120, "protein": 24.0, "carbs": 2.0, "fat": 1.5},
    {"name": "Queso PorSalut Light / Magro", "brand_or_notes": "Bajo en grasa", "serving_size": 30, "calories": 68, "protein": 6.5, "carbs": 0.5, "fat": 4.5},

    # Carbohidratos
    {"name": "Avena tradicional o instantánea", "brand_or_notes": "En seco", "serving_size": 100, "calories": 389, "protein": 16.9, "carbs": 66.3, "fat": 6.9},
    {"name": "Arroz blanco cocido", "brand_or_notes": "Cocido al vapor", "serving_size": 100, "calories": 130, "protein": 2.7, "carbs": 28.2, "fat": 0.3},
    {"name": "Arroz integral cocido", "brand_or_notes": "Cocido", "serving_size": 100, "calories": 112, "protein": 2.6, "carbs": 23.5, "fat": 0.9},
    {"name": "Papa / Patata hervida", "brand_or_notes": "Sin piel hervida", "serving_size": 100, "calories": 87, "protein": 1.9, "carbs": 20.1, "fat": 0.1},
    {"name": "Batata / Camote al horno", "brand_or_notes": "Cocido", "serving_size": 100, "calories": 90, "protein": 2.0, "carbs": 20.7, "fat": 0.2},
    {"name": "Pan integral", "brand_or_notes": "1 rebanada (~30g)", "serving_size": 30, "calories": 75, "protein": 3.5, "carbs": 13.0, "fat": 1.0},
    {"name": "Fideos / Pasta cocida", "brand_or_notes": "Al dente", "serving_size": 100, "calories": 158, "protein": 5.8, "carbs": 30.9, "fat": 0.9},

    # Frutas y Verduras
    {"name": "Banana / Plátano", "brand_or_notes": "1 unidad mediana (~100g)", "serving_size": 100, "calories": 89, "protein": 1.1, "carbs": 22.8, "fat": 0.3},
    {"name": "Manzana", "brand_or_notes": "Con cáscara", "serving_size": 100, "calories": 52, "protein": 0.3, "carbs": 13.8, "fat": 0.2},
    {"name": "Frutillas / Fresas", "brand_or_notes": "Frescas", "serving_size": 100, "calories": 33, "protein": 0.7, "carbs": 7.7, "fat": 0.3},
    {"name": "Arándanos", "brand_or_notes": "Frescos", "serving_size": 100, "calories": 57, "protein": 0.7, "carbs": 14.5, "fat": 0.3},
    {"name": "Espinaca cruda", "brand_or_notes": "Hojas frescas", "serving_size": 100, "calories": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4},
    {"name": "Brócoli cocido", "brand_or_notes": "Al vapor", "serving_size": 100, "calories": 35, "protein": 2.4, "carbs": 7.2, "fat": 0.4},
    {"name": "Tomate", "brand_or_notes": "Fresco", "serving_size": 100, "calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2},

    # Grasas saludables & Otros
    {"name": "Aceite de Oliva Extra Virgen", "brand_or_notes": "1 cucharada sopera (~10ml/g)", "serving_size": 10, "calories": 88, "protein": 0.0, "carbs": 0.0, "fat": 10.0},
    {"name": "Palta / Aguacate", "brand_or_notes": "Pulpa fresca", "serving_size": 100, "calories": 160, "protein": 2.0, "carbs": 8.5, "fat": 14.7},
    {"name": "Frutos Secos (Nueces/Almendras)", "brand_or_notes": "Mix natural", "serving_size": 30, "calories": 185, "protein": 5.0, "carbs": 6.0, "fat": 16.0},
    {"name": "Mantequilla de Maní natural", "brand_or_notes": "1 cucharada (~15g)", "serving_size": 15, "calories": 90, "protein": 4.0, "carbs": 3.0, "fat": 7.5},
]

class Command(BaseCommand):
    help = "Carga alimentos iniciales saludables para seguimiento de déficit calórico"

    def handle(self, *args, **options):
        created_count = 0
        for item in SAMPLE_FOODS:
            obj, created = FoodItem.objects.get_or_create(
                user=None,
                name=item["name"],
                defaults={
                    "brand_or_notes": item["brand_or_notes"],
                    "serving_size": Decimal(str(item["serving_size"])),
                    "calories": Decimal(str(item["calories"])),
                    "protein": Decimal(str(item["protein"])),
                    "carbs": Decimal(str(item["carbs"])),
                    "fat": Decimal(str(item["fat"])),
                    "is_favorite": True,
                }
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Alimentos cargados exitosamente: {created_count} nuevos."))
