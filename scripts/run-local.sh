#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Создайте .env из .env.example и укажите BOT_TOKEN"
  exit 1
fi

if ! curl -sf "http://localhost:8191/v1" -o /dev/null 2>&1; then
  echo "FlareSolverr не отвечает на http://localhost:8191"
  echo "1) Запустите Docker Desktop"
  echo "2) Выполните: docker run -d --name arent_flaresolverr -p 8191:8191 --restart unless-stopped ghcr.io/flaresolverr/flaresolverr:latest"
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3.11 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python -m app.main
