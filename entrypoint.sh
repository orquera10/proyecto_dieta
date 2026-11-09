#!/bin/sh
set -e

echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "==> Precargando catálogo inicial de alimentos..."
python manage.py seed_foods || true

echo "==> Iniciando servidor Gunicorn en puerto 8000..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 config.wsgi:application
