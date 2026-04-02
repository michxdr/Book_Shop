#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}"; do
    sleep 1
done
echo "==> PostgreSQL is ready!"

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting application..."
exec "$@"
