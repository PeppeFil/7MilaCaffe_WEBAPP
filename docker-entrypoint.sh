#!/usr/bin/env sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    flask --app run:app db upgrade
fi

if [ "${IMPORT_CATALOGO_REALE:-true}" = "true" ]; then
    flask --app run:app import-catalogo-reale
fi

if [ "${IMPORT_FATTURE_BORBONE_SETTEMBRE_2026:-true}" = "true" ]; then
    flask --app run:app carica-fatture-borbone-settembre-2026 --skip-catalog-sync
fi

exec "$@"
