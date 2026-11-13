#!/usr/bin/env bash
# EMSoft Support — Backup da stack completa
#
# Componentes: postgres, appwrite, qdrant, n8n, evolution, redis
# Cada componente só roda se o container estiver ativo; senão registra
# "SKIP <nome> (container ausente)" e segue para o próximo.
#
# Uso:
#   scripts/backup.sh [--help]
# Variáveis de ambiente:
#   BACKUP_DIR              diretório dos artefatos           (default ./backups)
#   BACKUP_RETENTION_DAYS   dias de retenção de artefatos     (default 14)
#   COMPOSE_FILE            compose principal da stack        (default infra/docker-compose.prod.yml)
#   BACKUP_ONLY             só estes componentes, "a,b,c"     (default: todos)
#   BACKUP_SKIP             pula estes componentes, "a,b"     (default: nenhum)
#
# Saída: artefatos em $BACKUP_DIR + manifesto $BACKUP_DIR/manifest_<data>.txt
# Exit code: 0 se todos os componentes rodados tiverem verificação OK; 1 caso contrário.

set -euo pipefail

usage() {
  sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/docker-compose.prod.yml}"
BACKUP_ONLY="${BACKUP_ONLY:-}"
BACKUP_SKIP="${BACKUP_SKIP:-}"

DATE="$(date +%Y%m%d_%H%M%S)"
HOST="$(hostname)"
mkdir -p "$BACKUP_DIR"

declare -A RESULTS=()
MANIFEST_LINES=()
ARTIFACT=""
SKIP_REASON=""

log() { echo "  $*"; }

# ---------------------------------------------------------------- helpers

is_enabled() {
  local comp="$1"
  [[ -n "$BACKUP_ONLY" ]] && [[ ",$BACKUP_ONLY," != *",$comp,"* ]] && return 1
  [[ -n "$BACKUP_SKIP" ]] && [[ ",$BACKUP_SKIP," == *",$comp,"* ]] && return 1
  return 0
}

compose_up() {
  local file="$1" svc="$2"
  docker compose -f "$file" ps -q "$svc" 2>/dev/null | grep -q .
}

container_up() {
  local name="$1"
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$name"
}

record() {
  # record <componente> <OK|FALHOU|SKIP> <arquivo> <sha256|-> <detalhe>
  local comp="$1" status="$2" file="$3" sha="$4" detail="$5"
  RESULTS["$comp"]="$status"
  local size="-"
  if [[ "$file" != "-" && -f "$file" ]]; then
    size="$(stat -c%s "$file")"
  fi
  MANIFEST_LINES+=("$(printf '%-10s %-8s arquivo=%s tamanho=%s sha256=%s %s' \
    "$comp" "$status" "$file" "$size" "$sha" "$detail")")
  echo "[$status] $comp — $detail"
}

verify_artifact() {
  # verify_artifact <arquivo> <gz|tar> → "OK" ou "FALHOU: <motivo>"
  local file="$1" kind="$2"
  # Tamanho mínimo = não-vazio: dumps de bancos vazios são pequenos mas válidos;
  # integridade + não-vazio é o critério correto, tamanho é só informativo no manifesto.
  local size
  size="$(stat -c%s "$file" 2>/dev/null || echo 0)"
  if [[ "$size" -le 0 ]]; then
    echo "FALHOU: arquivo vazio"
    return 0
  fi
  case "$kind" in
    gz)
      if ! gzip -t "$file" 2>/dev/null; then
        echo "FALHOU: gzip -t reprovou o arquivo"
      else
        echo "OK"
      fi
      ;;
    tar)
      local n
      n="$(tar -tzf "$file" 2>/dev/null | wc -l)"
      if [[ "$n" -gt 0 ]]; then
        echo "OK"
      else
        echo "FALHOU: tar vazio ou inválido"
      fi
      ;;
  esac
}

run_component() {
  local comp="$1"
  if ! is_enabled "$comp"; then
    record "$comp" "SKIP" "-" "-" "desabilitado por BACKUP_ONLY/BACKUP_SKIP"
    return 0
  fi
  ARTIFACT=""
  SKIP_REASON=""
  if "backup_${comp}"; then
    if [[ -z "$ARTIFACT" || ! -f "$ARTIFACT" ]]; then
      record "$comp" "FALHOU" "-" "-" "nada gerado (sem artefato)"
      return 0
    fi
    local kind res sha
    case "$ARTIFACT" in
      *.tar.gz) kind="tar" ;;
      *) kind="gz" ;;
    esac
    res="$(verify_artifact "$ARTIFACT" "$kind")"
    if [[ "$res" == "OK" ]]; then
      sha="$(sha256sum "$ARTIFACT" | awk '{print $1}')"
      record "$comp" "OK" "$ARTIFACT" "$sha" "verificação $kind OK"
    else
      record "$comp" "FALHOU" "$ARTIFACT" "-" "$res"
    fi
    return 0
  fi
  if [[ -n "$SKIP_REASON" ]]; then
    record "$comp" "SKIP" "-" "-" "$SKIP_REASON"
    return 0
  fi
  record "$comp" "FALHOU" "-" "-" "erro na execução do backup"
}

# ------------------------------------------------------------- componentes

backup_postgres() {
  if ! compose_up "$COMPOSE_FILE" postgres; then
    SKIP_REASON="container ausente"
    return 2
  fi
  # Usuário/banco vindos do env do próprio container (fallback: emsoft)
  local user db
  user="$(docker compose -f "$COMPOSE_FILE" exec -T postgres printenv POSTGRES_USER 2>/dev/null || true)"
  db="$(docker compose -f "$COMPOSE_FILE" exec -T postgres printenv POSTGRES_DB 2>/dev/null || true)"
  user="${user:-emsoft}"
  db="${db:-emsoft}"
  ARTIFACT="$BACKUP_DIR/postgres_${DATE}.sql.gz"
  log "pg_dump -U $user $db"
  if ! docker compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_dump -U "$user" --clean --if-exists "$db" | gzip > "$ARTIFACT"; then
    return 1
  fi
}

backup_appwrite() {
  # Appwrite vive em infra/appwrite/docker-compose.yml; banco principal:
  # container appwrite-mariadb (mariadb:10.11), env do banco já no container.
  # O 2>/dev/null interno descarta o aviso de senha na linha de comando.
  if ! container_up appwrite-mariadb; then
    SKIP_REASON="container ausente"
    return 2
  fi
  ARTIFACT="$BACKUP_DIR/appwrite_${DATE}.sql.gz"
  log "mariadb-dump (appwrite-mariadb)"
  if ! docker exec appwrite-mariadb sh -c \
      'mariadb-dump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --events "$MYSQL_DATABASE" 2>/dev/null' \
      | gzip > "$ARTIFACT"; then
    return 1
  fi
}

backup_qdrant() {
  # Abordagem: tar do diretório /qdrant/storage dentro do próprio container
  # (volume named qdrant-data). Rejeita-se a API de snapshots porque ela é
  # por coleção (POST /collections/<c>/snapshots) — não cobre o storage
  # inteiro; o tar é um único artefato e não depende de porta exposta.
  if ! compose_up "$COMPOSE_FILE" qdrant; then
    SKIP_REASON="container ausente"
    return 2
  fi
  ARTIFACT="$BACKUP_DIR/qdrant_${DATE}.tar.gz"
  log "tar -C /qdrant storage (via container qdrant)"
  if ! docker compose -f "$COMPOSE_FILE" exec -T qdrant \
      tar -czf - -C /qdrant storage > "$ARTIFACT"; then
    return 1
  fi
}

backup_n8n() {
  # /home/node/.n8n: sqlite + credenciais já criptografadas pelo próprio n8n
  if ! compose_up "$COMPOSE_FILE" n8n; then
    SKIP_REASON="container ausente"
    return 2
  fi
  ARTIFACT="$BACKUP_DIR/n8n_${DATE}.tar.gz"
  log "tar -C /home/node .n8n (via container n8n)"
  if ! docker compose -f "$COMPOSE_FILE" exec -T n8n \
      tar -czf - -C /home/node .n8n > "$ARTIFACT"; then
    return 1
  fi
}

backup_evolution() {
  # O serviço evolution-db pode existir só no compose de dev
  local file="$COMPOSE_FILE"
  if ! compose_up "$file" evolution-db; then
    if compose_up "infra/docker-compose.dev.yml" evolution-db; then
      file="infra/docker-compose.dev.yml"
    else
      SKIP_REASON="container ausente"
      return 2
    fi
  fi
  ARTIFACT="$BACKUP_DIR/evolution_${DATE}.sql.gz"
  log "pg_dump -U evolution evolution (compose: $file)"
  if ! docker compose -f "$file" exec -T evolution-db \
      pg_dump -U evolution evolution | gzip > "$ARTIFACT"; then
    return 1
  fi
}

backup_redis() {
  # Decisão: SKIP permanente. O Redis aqui é cache descartável (sessões,
  # fila de jobs) — os dados reais vivem no postgres/appwrite. Forçar RDB
  # exigiria SAVE + detectar o caminho do dump (que varia entre versões da
  # imagem: /data vs /data/app-data) + docker cp; o custo não compensa o
  # valor recuperável. Se um dia o Redis guardar estado importante, este
  # componente é o lugar para implementá-lo de verdade.
  SKIP_REASON="cache descartável (ver comentário no backup_redis)"
  return 2
}

# ------------------------------------------------------------- retenção

apply_retention() {
  local deleted
  deleted="$(find "$BACKUP_DIR" -maxdepth 1 -type f \
    \( -name '*.sql.gz' -o -name '*.tar.gz' -o -name 'manifest_*.txt' \) \
    -mtime +"$BACKUP_RETENTION_DAYS" -print -delete | wc -l)"
  echo "Retenção: ${deleted} artefato(s) com mais de ${BACKUP_RETENTION_DAYS} dia(s) removidos de $BACKUP_DIR"
}

# ------------------------------------------------------------------ main

echo "=== EMSoft Support - Backup ==="
echo "Data: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Host: $HOST"
echo "Compose: $COMPOSE_FILE"
echo "Diretório: $BACKUP_DIR | Retenção: ${BACKUP_RETENTION_DAYS} dias"
echo

MANIFEST="$BACKUP_DIR/manifest_${DATE}.txt"
{
  echo "EMSoft Support - Backup"
  echo "Data:   $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Host:   $HOST"
  echo "Compose: $COMPOSE_FILE"
  echo "Retenção: $BACKUP_RETENTION_DAYS dias"
  echo
} > "$MANIFEST"

for comp in postgres appwrite qdrant n8n evolution redis; do
  run_component "$comp"
done

{
  printf '%s\n' "${MANIFEST_LINES[@]}"
} >> "$MANIFEST"

apply_retention

echo
echo "=== Resumo ==="
FAILED=0
for comp in postgres appwrite qdrant n8n evolution redis; do
  status="${RESULTS[$comp]:-NÃO EXECUTADO}"
  printf '%-10s %s\n' "$comp" "$status"
  [[ "$status" == "FALHOU" ]] && FAILED=1
done
echo
echo "Manifesto: $MANIFEST"

exit "$FAILED"
