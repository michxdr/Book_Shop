#!/bin/bash
set -e

mkdir -p /app/logs

if [ "${SKIP_INIT}" != "true" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear

    echo "Creating superuser if needed..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@warehouse.local', 'adminpass123', role='admin')
    print('Superuser created.')
else:
    print('Superuser already exists.')
" || true
fi

exec "$@"
