#!/usr/bin/env sh
set -eu

# Make mounted volumes writable for the non-root app user.
# (Named volumes are root-owned by default on first use.)
if [ "$(id -u)" = "0" ]; then
  for d in /app/logs /app/data; do
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

  if [ "${DJANGO_CREATE_SUPERUSER:-0}" = "1" ]; then
    if [ -z "${DJANGO_SUPERUSER_USERNAME:-}" ] || [ -z "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
      echo "[entrypoint] DJANGO_CREATE_SUPERUSER=1 ですが、DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD が未設定です。スキップします。" >&2
    else
      echo "[entrypoint] Ensuring superuser exists..."
      su -s /bin/sh appuser -c "/app/.venv/bin/python -c \"import os; from django.contrib.auth import get_user_model; User=get_user_model(); u=os.environ['DJANGO_SUPERUSER_USERNAME']; p=os.environ['DJANGO_SUPERUSER_PASSWORD']; e=os.environ.get('DJANGO_SUPERUSER_EMAIL',''); exists=User._default_manager.filter(username=u).exists(); (print('Superuser already exists:', u) if exists else (User._default_manager.create_superuser(u, e, p), print('Created superuser:', u)))\""
    fi
  fi

  exec su -s /bin/sh appuser -c "/app/.venv/bin/gunicorn django_todo.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-30} --access-logfile - --error-logfile - --capture-output"
fi

# If the container is started as non-root, just run the provided command.
exec "$@"
