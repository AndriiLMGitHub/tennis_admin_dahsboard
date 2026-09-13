#!/usr/bin/env sh
set -eu

cd /app/src

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-false}" = "true" ]; then
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
