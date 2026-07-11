#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    flask --app run:app db upgrade
fi

exec "$@"
