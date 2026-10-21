#!/bin/sh
set -e

echo ">> Waiting for database..."
python manage.py wait_for_db

echo ">> Applying migrations..."
python manage.py migrate --noinput

echo ">> Collecting static files..."
python manage.py collectstatic --noinput >/dev/null

if [ "${SEED_DEMO:-0}" = "1" ]; then
  echo ">> Seeding demo data..."
  python manage.py seed_demo
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  echo ">> Ensuring superuser '${DJANGO_SUPERUSER_USERNAME}' exists..."
  python manage.py createsuperuser --noinput 2>/dev/null || true
fi

echo ">> Starting: $*"
exec "$@"
