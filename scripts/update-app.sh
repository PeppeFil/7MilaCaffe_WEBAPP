#!/usr/bin/env bash
set -euo pipefail

cd /root/7milacaffe
docker compose pull app
docker compose up -d --no-deps app
docker image prune -f
