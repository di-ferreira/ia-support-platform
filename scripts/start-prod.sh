#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${1:-infra/.env.prod}"
COMPOSE_FILE="infra/docker-compose.prod.yml"

echo "=== Starting EMSoft Support - Production ==="
echo "Using compose file: $COMPOSE_FILE"
echo "Using env file: $ENV_FILE"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Environment file $ENV_FILE not found."
  echo "Copy infra/.env.example to $ENV_FILE and configure it."
  exit 1
fi

# Carrega o .env com source em vez de grep|xargs: grep|xargs quebra valores
# com espaços ou aspas (ex.: CORS_ORIGINS); source interpreta o arquivo como
# bash e preserva esses valores. set -a/exporta tudo o que for definido.
set -a
source "$ENV_FILE"
set +a

echo "Pulling latest images..."
# --ignore-buildable: backend e frontend são definidos com `build:` (não vêm do
# registry); sem a flag, o pull falharia tentando baixar imagens que não existem.
docker compose -f "$COMPOSE_FILE" pull --ignore-buildable

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

# A pilha de produção não publica porta do backend no host (o tráfego entra
# pelo Traefik), então a sondagem de saúde roda DENTRO do container. A imagem
# (python:3.12-slim) não tem curl nem wget, por isso a sonda usa python3/urllib
# — a mesma sonda do HEALTHCHECK da imagem (backend/Dockerfile).
SAUDE_SONDA="docker compose -f $COMPOSE_FILE exec -T backend python3 -c 'import sys,urllib.request;urllib.request.urlopen(sys.argv[1],timeout=5)'"

# esperar_saude <url> <segundos>
# Sonda a URL a cada 5s, imprimindo a tentativa; sai com exit 1 e mensagem
# clara se não responder em <segundos>. Usa SAUDE_SONDA quando definida
# (sonda em container); senão, fallback para curl local (permite testar a
# função do host contra uma porta publicada, ex.: o dev em :8001).
esperar_saude() {
  local url="$1" timeout="$2" inicio tentativas sonda
  inicio=$(date +%s)
  tentativas=0
  sonda="${SAUDE_SONDA:-curl -fsS -o /dev/null}"
  while true; do
    tentativas=$((tentativas + 1))
    if bash -c "$sonda \"\$1\"" _ "$url" 2>/dev/null; then
      echo "  OK: $url respondeu após $tentativas tentativa(s)."
      return 0
    fi
    if [ $(( $(date +%s) - inicio )) -ge "$timeout" ]; then
      echo "Error: timeout de ${timeout}s aguardando $url."
      echo "O backend não ficou saudável a tempo. Verifique com: docker compose -f $COMPOSE_FILE logs backend"
      exit 1
    fi
    echo "  aguardando $url (tentativa $tentativas)..."
    sleep 5
  done
}

echo "Waiting for backend liveness (/health)..."
esperar_saude "http://127.0.0.1:8000/health" 90

echo "Waiting for backend readiness (/health/ready)..."
esperar_saude "http://127.0.0.1:8000/health/ready" 120

echo "=== Deployment complete ==="
echo "Frontend: https://app.emsoft.app"
echo "Backend:  https://api.emsoft.app"
echo "n8n:      https://n8n.emsoft.app"

docker compose -f "$COMPOSE_FILE" ps --format 'table {{.Service}}\t{{.Status}}' | head -15
