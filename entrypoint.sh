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
      su -s /bin/sh appuser -c "/app/.venv/bin/python manage.py shell -c 'import os; from django.contrib.auth import get_user_model; User=get_user_model(); username=os.environ["DJANGO_SUPERUSER_USERNAME"]; password=os.environ["DJANGO_SUPERUSER_PASSWORD"]; email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""); update_pw=os.environ.get("DJANGO_SUPERUSER_UPDATE_PASSWORD", "0") == "1"; user, created=User._default_manager.get_or_create(username=username, defaults={"email": email, "is_staff": True, "is_superuser": True}); changed=False; \
  (setattr(user, "is_staff", True), setattr(user, "is_superuser", True), setattr(user, "email", email) if email else None); \
  (user.set_password(password), setattr(user, "email", email) if email else None, user.save(), print("Created superuser:", username)) if created else (user.set_password(password), user.save(), print("Updated superuser password:", username)) if update_pw else print("Superuser already exists:", username)'"
    fi
  fi

  exec su -s /bin/sh appuser -c "/app/.venv/bin/gunicorn django_todo.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-30} --access-logfile - --error-logfile - --capture-output"
fi

# If the container is started as non-root, just run the provided command.
exec "$@"
