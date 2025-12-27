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

  exec su -s /bin/sh appuser -c "/app/.venv/bin/gunicorn django_todo.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-30} --access-logfile - --error-logfile - --capture-output"
fi

# If the container is started as non-root, just run the provided command.
exec "$@"
