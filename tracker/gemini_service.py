import os
import json
import time
import logging
import urllib.request
import urllib.error
from decimal import Decimal

logger = logging.getLogger(__name__)

PRIMARY_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
FALLBACK_MODELS = ['gemini-2.5-flash', 'gemini-flash-latest']


def call_gemini_api(prompt=None, parts=None, system_instruction=None, temperature=0.2):
    """
    Realiza una llamada robusta a la API de Gemini (Google AI Studio)
    con respuesta estructurada JSON, soporte multimodal (texto e imágenes),
    reintentos y modelo de respaldo si hay alta demanda (503).
    """
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return {"error": "No se ha configurado la clave API de Gemini (GEMINI_API_KEY)."}

    models_to_try = [os.environ.get('GEMINI_MODEL', PRIMARY_MODEL)] + FALLBACK_MODELS

    if parts is None:
        parts = [{"text": prompt or ""}]

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": temperature
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    last_error = None

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=20) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidates = res_data.get('candidates', [])
                    if not candidates:
                        continue

                    text_result = candidates[0]['content']['parts'][0]['text'].strip()
                    parsed = json.loads(text_result)
                    return {"success": True, "data": parsed, "model": model}

            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8', errors='ignore')
                last_error = f"HTTP {e.code}: {error_body}"
                logger.warning(f"Gemini {model} attempt {attempt+1} failed with {last_error}")
                if e.code in (503, 429):
                    time.sleep(1.0)
                    continue  # Retry or fallback to next model
                else:
                    break  # Non-retryable error
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini {model} attempt {attempt+1} exception: {e}")
                time.sleep(0.5)

    return {"error": f"Error comunicando con Gemini: {last_error}"}


def parse_meal_with_gemini(user_text="", image_b64=None, image_mime_type="image/jpeg", default_meal_type='almuerzo'):
    """
    Analiza una descripción de comida en lenguaje natural y/o una imagen del plato
    utilizando Gemini 3.5 Flash Lite y devuelve la lista de alimentos con sus macros calculados.
    """
    system_instruction = (
        "Eres un nutricionista experto y calculadora calórica precisa de referencia mundial con visión computacional. "
        "El usuario te proporcionará una fotografía de su comida, una descripción en texto, o ambas cosas combinadas. "
        "Tu tarea es: "
        "1. Si hay una imagen, analiza minuciosamente los alimentos que componen el plato o la comida visible. "
        "2. Usa cualquier texto o aclaración que el usuario proporcione para afinar detalles de preparación (ej: si es frito o al horno, si lleva manteca, tipo de queso, etc.). "
        "3. Desglosa los alimentos individuales en porciones realistas (estimando peso en gramos o mililitros según el tamaño visual). "
        "4. Calcula con precisión las calorías totales y macronutrientes (proteínas, carbohidratos y grasas en gramos) para cada alimento. "
        f"Si el usuario no especifica el momento del día, asume '{default_meal_type}'. "
        "Los tipos de comida permitidos son: 'desayuno', 'almuerzo', 'merienda', 'cena', 'snack'. "
        "Debes responder EXCLUSIVAMENTE con un JSON que sea un array de objetos con las siguientes claves: "
        "- name: string (nombre del alimento en español, claro y descriptivo) "
        "- grams: float o int (peso estimado de la porción en gramos o ml) "
        "- calories: float o int (calorías totales de esa porción) "
        "- protein: float o int (proteínas totales en gramos) "
        "- carbs: float o int (carbohidratos totales en gramos) "
        "- fat: float o int (grasas totales en gramos) "
        "- meal_type: string (uno de: 'desayuno', 'almuerzo', 'merienda', 'cena', 'snack')"
    )

    parts = []

    if image_b64:
        parts.append({
            "inline_data": {
                "mime_type": image_mime_type or "image/jpeg",
                "data": image_b64
            }
        })

    prompt_text = "Comida del usuario a analizar:"
    if user_text:
        prompt_text += f"\nDescripción y detalles adicionales del usuario: \"{user_text}\""
    if image_b64:
        prompt_text += "\nPor favor analiza la fotografía del plato adjunto e identifica todos los alimentos y cantidades."

    parts.append({"text": prompt_text})

    res = call_gemini_api(parts=parts, system_instruction=system_instruction)
    if "error" in res:
        return res

    parsed_foods = res["data"]
    if not isinstance(parsed_foods, list):
        if isinstance(parsed_foods, dict) and 'foods' in parsed_foods:
            parsed_foods = parsed_foods['foods']
        elif isinstance(parsed_foods, dict) and 'items' in parsed_foods:
            parsed_foods = parsed_foods['items']
        else:
            parsed_foods = [parsed_foods]

    normalized = []
    for item in parsed_foods:
        meal_type = item.get('meal_type', default_meal_type).lower()
        if meal_type not in ['desayuno', 'almuerzo', 'merienda', 'cena', 'snack']:
            meal_type = default_meal_type

        normalized.append({
            "name": str(item.get('name', 'Alimento no identificado')).strip(),
            "grams": max(1.0, float(item.get('grams', 100.0))),
            "calories": max(0.0, float(item.get('calories', 0.0))),
            "protein": max(0.0, float(item.get('protein', 0.0))),
            "carbs": max(0.0, float(item.get('carbs', 0.0))),
            "fat": max(0.0, float(item.get('fat', 0.0))),
            "meal_type": meal_type,
        })

    return {"success": True, "foods": normalized, "model": res.get("model")}


def estimate_food_nutrition_with_gemini(food_query):
    """
    Estima la información nutricional completa para dar de alta o autocompletar
    un alimento en el catálogo utilizando Gemini 3.5 Flash Lite.
    """
    system_instruction = (
        "Eres un nutricionista y base de datos de alimentos de referencia internacional. "
        "A partir del nombre o descripción de un alimento o producto, calcula su información nutricional promedio. "
        "Si no se especifica el tamaño de porción, asume 100 gramos como base estándar. "
        "Devuelve EXCLUSIVAMENTE un objeto JSON con las siguientes claves exactas: "
        "- name: string (nombre limpio y representativo del alimento en español) "
        "- brand_or_notes: string (marca, forma de cocción o detalle de la porción) "
        "- serving_size: float o int (tamaño de la porción base en gramos, habitualmente 100.0) "
        "- calories: float o int (calorías para esa porción base) "
        "- protein: float o int (gramos de proteína) "
        "- carbs: float o int (gramos de carbohidratos) "
        "- fat: float o int (gramos de grasa)"
    )

    prompt = f"Estimar valores nutricionales para:\n\"{food_query}\""

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if "error" in res:
        return res

    item = res["data"]
    if isinstance(item, list) and len(item) > 0:
        item = item[0]

    serving_size = max(1.0, float(item.get('serving_size', 100.0)))
    return {
        "success": True,
        "name": str(item.get('name', food_query)).strip(),
        "brand_or_notes": str(item.get('brand_or_notes', 'Estimado con Gemini')).strip(),
        "serving_size": serving_size,
        "calories": max(0.0, float(item.get('calories', 0.0))),
        "protein": max(0.0, float(item.get('protein', 0.0))),
        "carbs": max(0.0, float(item.get('carbs', 0.0))),
        "fat": max(0.0, float(item.get('fat', 0.0))),
        "model": res.get("model")
    }


def calculate_deficit_with_gemini(data):
    """
    Calcula el TDEE, objetivo de déficit y macronutrientes personalizados
    a partir de un cuestionario interactivo de usuario utilizando Gemini 3.5 Flash Lite.
    """
    gender = data.get('gender', 'M')
    age = data.get('age', 25)
    height = data.get('height', 175)
    current_weight = data.get('current_weight', 80)
    target_weight = data.get('target_weight', 75)
    activity_level = data.get('activity_level', 'moderado')
    deficit_rate = data.get('deficit_rate', 'moderado')
    notes = data.get('notes', '')

    system_instruction = (
        "Eres un nutricionista deportivo y fisiólogo de primer nivel especializado en recomposición corporal y déficit calórico sostenible. "
        "A partir de los siguientes datos del usuario, calcula su TDEE (Gasto Energético Diario Total), "
        "su objetivo calórico óptimo en déficit, y la repartición exacta de macronutrientes (proteínas, carbohidratos, grasas). "
        "Requisitos científicos: "
        "- Fórmula base recomendada: Mifflin-St Jeor ajustada por factor de actividad física. "
        "- Para déficit calórico preservando masa muscular: Proteínas entre 1.8g y 2.2g por kg de peso corporal. "
        "- Grasas saludables mínimas para función hormonal: entre 0.6g y 0.9g por kg. "
        "- El resto de las calorías debe cubrirse con carbohidratos (4 kcal/g). "
        "- Debes estimar las semanas que tardará en alcanzar su peso objetivo de forma saludable (~0.5kg a 1kg por semana según el déficit). "
        "Debes responder EXCLUSIVAMENTE con un JSON con los siguientes campos numéricos y de texto: "
        "- maintenance_calories: int (calorías de mantenimiento / TDEE) "
        "- daily_calorie_target: int (calorías diarias recomendadas con el déficit) "
        "- deficit_calories: int (diferencia diaria entre mantenimiento y objetivo) "
        "- deficit_percentage: int (porcentaje de déficit respecto al TDEE, ej: 20) "
        "- protein_target_g: int (gramos diarios de proteína) "
        "- carbs_target_g: int (gramos diarios de carbohidratos) "
        "- fat_target_g: int (gramos diarios de grasas) "
        "- estimated_weeks: int (semanas estimadas para alcanzar el peso objetivo) "
        "- weekly_loss_kg: float (pérdida estimada en kg por semana, ej: 0.5) "
        "- summary: string (explicación amigable de 2 a 3 oraciones en español sobre por qué se eligieron estas cifras) "
        "- tips: array de strings (3 o 4 consejos clave de adherencia, hidratación y entrenamiento específicos para este caso)"
    )

    prompt = (
        f"Datos del usuario para el plan de déficit calórico:\n"
        f"- Sexo: {'Masculino' if gender == 'M' else 'Femenino'}\n"
        f"- Edad: {age} años\n"
        f"- Altura: {height} cm\n"
        f"- Peso actual: {current_weight} kg\n"
        f"- Peso objetivo: {target_weight} kg\n"
        f"- Nivel de actividad: {activity_level}\n"
        f"- Ritmo deseado de déficit: {deficit_rate}\n"
        f"- Detalles adicionales de su rutina / entrenamiento: {notes or 'Ninguna'}\n"
    )

    res = call_gemini_api(prompt, system_instruction=system_instruction)
    if "error" in res:
        return res

    calc = res["data"]
    calc["success"] = True
    calc["model"] = res.get("model")
    return calc
