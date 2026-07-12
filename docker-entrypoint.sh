#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    flask --app run:app db upgrade
fi

if [ "${IMPORT_CATALOGO_REALE:-true}" = "true" ]; then
    flask --app run:app import-catalogo-reale
fi

exec "$@"
