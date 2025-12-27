#!/usr/bin/env sh
set -eu

# Make mounted volumes writable for the non-root app user.
# (Named volumes are root-owned by default on first use.)
if [ "$(id -u)" = "0" ]; then
  for d in /app/logs; do
    if [ -d "$d" ]; then
      chown -R appuser:appgroup "$d" || true
      chmod -R u+rwX,g+rwX "$d" || true
    fi
  done

  if [ "$#" -gt 0 ]; then
    exec su -s /bin/sh appuser -c "$*"
  fi

  if [ "${DJANGO_AUTO_MIGRATE:-1}" != "0" ]; then
    echo "[entrypoint] Running migrations..."
    su -s /bin/sh appuser -c "/app/.venv/bin/python manage.py migrate --noinput"
  fi

  # Create superuser if credentials are provided and user doesn't exist
  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "[entrypoint] Checking superuser..."
    su -s /bin/sh appuser -c "/app/.venv/bin/python manage.py shell -c \"from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists() else 1)\""
    if [ $? -ne 0 ]; then
      echo "[entrypoint] Creating superuser..."
      su -s /bin/sh appuser -c "/app/.venv/bin/python manage.py createsuperuser --noinput"
    else
      echo "[entrypoint] Superuser already exists, skipping."
    fi
  fi

  exec su -s /bin/sh appuser -c "/app/.venv/bin/gunicorn django_todo.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-30} --access-logfile - --error-logfile - --capture-output"
fi

# If the container is started as non-root, just run the provided command.
exec "$@"
