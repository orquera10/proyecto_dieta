FROM python:3.12-slim

# Evita que python genere archivos .pyc y fuerza buffer directo a stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Instalar dependencias de sistema necesarias para psycopg2 y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . /app/

# Crear directorios para archivos multimedia subidos
RUN mkdir -p /app/media/meal_photos /app/media/food_photos

# Recopilar archivos estáticos para WhiteNoise
RUN python manage.py collectstatic --noinput

# Dar permisos de ejecución al script de arranque
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
