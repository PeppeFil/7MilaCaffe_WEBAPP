#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Uso: bash configure-production-env.sh NOME_DOMINIO"
  exit 1
fi

DOMAIN="$1"
APP_IMAGE="ghcr.io/peppefil/7milacaffe-webapp:latest"

read -r -s -p "Incolla la DATABASE_URL Supabase (Session pooler): " DATABASE_URL
echo
read -r -p "Username amministratore [admin]: " ADMIN_USERNAME
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
read -r -p "Email amministratore: " ADMIN_EMAIL

while [[ -z "${ADMIN_EMAIL}" ]]; do
  read -r -p "L'email e obbligatoria: " ADMIN_EMAIL
done

read -r -s -p "Password amministratore: " ADMIN_PASSWORD
echo
read -r -s -p "Ripeti password amministratore: " ADMIN_PASSWORD_CONFIRM
echo

if [[ -z "${DATABASE_URL}" || -z "${ADMIN_PASSWORD}" ]]; then
  echo "DATABASE_URL e password amministratore sono obbligatorie."
  exit 1
fi

if [[ "${ADMIN_PASSWORD}" != "${ADMIN_PASSWORD_CONFIRM}" ]]; then
  echo "Le password non coincidono. Nessun file e stato creato."
  exit 1
fi

SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n')"

umask 077
cat > .env <<EOF
DOMAIN=${DOMAIN}
APP_IMAGE=${APP_IMAGE}
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=${DATABASE_URL}
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
EOF
chmod 600 .env

echo "Configurazione salvata in $(pwd)/.env"
echo "Non condividere questo file e non caricarlo su GitHub."
