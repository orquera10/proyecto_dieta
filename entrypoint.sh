#!/bin/sh
set -e

echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

echo "==> Precargando catálogo inicial de alimentos..."
python manage.py seed_foods || true

echo "==> Asegurando usuario administrador dario..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(username='dario', defaults={'email': 'dario@test.com', 'is_superuser': True, 'is_staff': True})
u.set_password('Tuxx6393@')
u.is_superuser = True
u.is_staff = True
u.save()
if hasattr(u, 'profile'):
    u.profile.save()
print('==> Usuario dario asegurado exitosamente con credenciales de administrador.')
" || true

echo "==> Iniciando servidor Gunicorn en puerto 8000..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 config.wsgi:application
