import os
import json
import logging
import urllib.request
import urllib.error
from decimal import Decimal

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')


def parse_meal_with_gemini(user_text, default_meal_type='almuerzo'):
    """
    Analiza una descripción de comida en lenguaje natural (ej: '3 albondigas con pure')
    utilizando Gemini 3.5 Flash Lite y devuelve la lista de alimentos con sus macros calculados.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '')
    model = os.environ.get('GEMINI_MODEL', DEFAULT_MODEL)

    if not api_key:
        return {"error": "No se ha configurado la clave API de Gemini."}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    system_instructions = (
        "Eres un nutricionista experto y calculadora calórica precisa. "
        "El usuario describirá lo que comió en lenguaje cotidiano (español), "
        "por ejemplo: 'como 3 albóndigas con una porción de puré' o 'un café con leche y 2 tostadas con palta'. "
        "Tu tarea es desglosar los alimentos individuales en porciones realistas y estimar sus valores nutricionales. "
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

    prompt = f"{system_instructions}\n\nComida del usuario:\n\"{user_text}\""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            candidates = res_data.get('candidates', [])
            if not candidates:
                return {"error": "Gemini no devolvió ninguna respuesta para este texto."}

            text_result = candidates[0]['content']['parts'][0]['text'].strip()
            # Parse JSON
            parsed_foods = json.loads(text_result)
            if not isinstance(parsed_foods, list):
                if isinstance(parsed_foods, dict) and 'foods' in parsed_foods:
                    parsed_foods = parsed_foods['foods']
                elif isinstance(parsed_foods, dict) and 'items' in parsed_foods:
                    parsed_foods = parsed_foods['items']
                else:
                    parsed_foods = [parsed_foods]

            # Normalize values
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

            return {"success": True, "foods": normalized}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Gemini API HTTP Error {e.code}: {error_body}")
        return {"error": f"Error de comunicación con Gemini ({e.code}): {error_body}"}
    except Exception as e:
        logger.error(f"Error parseando comida con Gemini: {e}")
        return {"error": f"Error al procesar con IA: {str(e)}"}
