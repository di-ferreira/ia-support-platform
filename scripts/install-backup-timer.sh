#!/usr/bin/env bash
# EMSoft Support — instala o agendamento do backup (systemd timer).
#
# Instala infra/systemd/emsoft-backup.{service,timer} e deixa o timer
# habilitado. Modo **user** por default (units em ~/.config/systemd/user/);
# modo **system** com --system (units em /etc/systemd/system/, sudo usado
# APENAS para copiar as units e o daemon-reload — nunca para rodar o backup).
#
# Uso:
#   scripts/install-backup-timer.sh [--help] [--system] [--uninstall] [--dry-run]
#
# Comportamento:
#   - substitui o placeholder __REPO__ pelo realpath deste repositório;
#   - cria ~/.config/emsoft-backup.env a partir de backup.env.example
#     apenas se ainda não existir;
#   - modo --system: o EnvironmentFile vira /etc/emsoft-backup.env (criado
#     do example, se ausente — %h num unit de sistema resolveria para /root);
#   - idempotente: rodar duas vezes só reinstala as units (o env é preservado);
#   - --dry-run: imprime os comandos que rodaria, sem executar.
#
# Requisito: systemd com user manager (modo user) — precisa de sessão do
# usuário; sem XDG_RUNTIME_DIR, ver o aviso do próprio script (lingering).

set -euo pipefail

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; }

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

MODE="user"
UNINSTALL=0
DRY_RUN="${DRY_RUN:-0}"
for arg in "$@"; do
  case "$arg" in
    --system)    MODE="system" ;;
    --uninstall) UNINSTALL=1 ;;
    --dry-run)   DRY_RUN=1 ;;
    -h|--help)   usage; exit 0 ;;
    *) echo "opção desconhecida: $arg" >&2; usage; exit 2 ;;
  esac
done

run() { # imprime o comando; só executa se DRY_RUN=0
  echo "+ $*"
  if [[ "$DRY_RUN" -eq 0 ]]; then "$@"; fi
}

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNITS_SRC="$REPO/infra/systemd"
if [[ "$MODE" == "system" ]]; then
  ENV_FILE="/etc/emsoft-backup.env"
else
  ENV_FILE="$HOME/.config/emsoft-backup.env"
fi

TMP_FILE=""
cleanup() { if [[ -n "$TMP_FILE" ]]; then rm -f "$TMP_FILE"; fi; }
trap cleanup EXIT

systemctl_for() { # user|system → imprime o systemctl certo
  if [[ "$MODE" == "system" ]]; then echo "systemctl"; else echo "systemctl --user"; fi
}

install_units() {
  local unit
  if [[ ! -f "$UNITS_SRC/emsoft-backup.service" || ! -f "$UNITS_SRC/emsoft-backup.timer" ]]; then
    echo "erro: templates ausentes em $UNITS_SRC" >&2
    exit 1
  fi

  if [[ "$MODE" == "system" ]]; then
    DEST="/etc/systemd/system"
    command -v sudo >/dev/null || { echo "erro: --system requer sudo" >&2; exit 1; }
    # mktemp: process substitution (/dev/fd/N) não sobrevive ao sudo, que
    # fecha os fds extras por padrão.
    TMP_FILE="$(mktemp /tmp/emsoft-backup-unit.XXXXXX)"
    for unit in emsoft-backup.service emsoft-backup.timer; do
      # %h num unit de sistema resolveria para o home do root (/root);
      # em modo system o env vive em /etc.
      sed "s|__REPO__|$REPO|g; s|EnvironmentFile=-%h/.config/emsoft-backup.env|EnvironmentFile=-/etc/emsoft-backup.env|" \
        "$UNITS_SRC/$unit" > "$TMP_FILE"
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "--- $unit (seria instalado em $DEST/$unit) ---"
        cat "$TMP_FILE"
      fi
      run sudo install -m 0644 "$TMP_FILE" "$DEST/$unit"
    done
    run sudo systemctl daemon-reload
  else
    DEST="$HOME/.config/systemd/user"
    if [[ "$DRY_RUN" -eq 0 ]]; then
      mkdir -p "$DEST"
      for unit in emsoft-backup.service emsoft-backup.timer; do
        sed "s|__REPO__|$REPO|g" "$UNITS_SRC/$unit" > "$DEST/$unit"
      done
    else
      for unit in emsoft-backup.service emsoft-backup.timer; do
        echo "+ sed 's|__REPO__|$REPO|g' $UNITS_SRC/$unit > $DEST/$unit"
      done
    fi
    run systemctl --user daemon-reload
  fi
  echo "Units instaladas em $DEST (__REPO__ → $REPO)"
}

create_env_if_missing() {
  if [[ -e "$ENV_FILE" ]]; then
    echo "env já existe, preservado: $ENV_FILE"
    return 0
  fi
  if [[ "$MODE" == "system" ]]; then
    # Não copia do $HOME do usuário sem avisar: parte do example.
    run sudo install -m 0600 "$UNITS_SRC/backup.env.example" "$ENV_FILE"
  else
    if [[ "$DRY_RUN" -eq 0 ]]; then
      mkdir -p "$(dirname "$ENV_FILE")"
      cp "$UNITS_SRC/backup.env.example" "$ENV_FILE"
      chmod 600 "$ENV_FILE"
    else
      echo "+ cp $UNITS_SRC/backup.env.example $ENV_FILE && chmod 600 $ENV_FILE"
    fi
  fi
  echo "env criado a partir do example: $ENV_FILE"
  if [[ -n "${DOCKER_CONFIG:-}" ]]; then
    echo "docker usa um DOCKER_CONFIG não padrão (${DOCKER_CONFIG}): o backup" >&2
    echo "roda sem TTY/sessão — adicione DOCKER_CONFIG=${DOCKER_CONFIG}" >&2
    echo "ao $ENV_FILE (e garanta acesso ao socket docker pelo usuário)." >&2
  fi
}

uninstall() {
  local sc
  sc="$(systemctl_for)"
  local dest
  if [[ "$MODE" == "system" ]]; then
    dest="/etc/systemd/system"
    run sudo $sc disable --now emsoft-backup.timer 2>/dev/null || true
    run sudo $sc disable --now emsoft-backup.service 2>/dev/null || true
    run sudo rm -f "$dest/emsoft-backup.service" "$dest/emsoft-backup.timer"
    run sudo systemctl daemon-reload
  else
    dest="$HOME/.config/systemd/user"
    run $sc disable --now emsoft-backup.timer 2>/dev/null || true
    run rm -f "$dest/emsoft-backup.service" "$dest/emsoft-backup.timer"
    run $sc daemon-reload
  fi
  echo "Units removidas de $dest (o $ENV_FILE foi preservado)."
}

check_user_session() {
  # Só se aplica ao modo user; o backup em si nunca precisa de root.
  if [[ "$MODE" == "system" || "$DRY_RUN" -eq 1 ]]; then
    return 0
  fi
  if ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "AVISO: o user manager do systemd não respondeu" >&2
    echo "(systemctl --user precisa de sessão do usuário)." >&2
    if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
      echo "XDG_RUNTIME_DIR não existe — o user manager não sobe sem ele." >&2
      echo "Habilite o lingering para o user manager persistir fora da sessão:" >&2
      echo "    loginctl enable-linger $USER" >&2
      echo "Depois reabra uma sessão e rode este script novamente." >&2
    fi
    exit 1
  fi
}

if [[ "$UNINSTALL" -eq 1 ]]; then
  check_user_session
  uninstall
  exit 0
fi

check_user_session
install_units
create_env_if_missing

sc="$(systemctl_for)"
if [[ "$MODE" == "system" ]]; then
  run sudo $sc enable --now emsoft-backup.timer
else
  run $sc enable --now emsoft-backup.timer
fi
echo
echo "Proximos disparos:"
run $sc list-timers emsoft-backup.timer --no-pager | head -5
echo
echo "Teste manual: $sc start emsoft-backup.service && $sc status emsoft-backup.service --no-pager"
