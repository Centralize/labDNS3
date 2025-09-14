#!/usr/bin/env bash
# labdns.sh - simple service helper for labDNS (start/stop/restart/status/install/remove)
# Requires: labdns (CLI) in PATH

set -euo pipefail

# Defaults (override via env)
INTERFACE=${INTERFACE:-127.0.0.1}
PORT=${PORT:-5353}
ZONES_DIR=${ZONES_DIR:-$(pwd)/zones}
ZONEFILE=${ZONEFILE:-}
PID_FILE=${PID_FILE:-$(pwd)/labdns.pid}
LOG_FILE=${LOG_FILE:-$(pwd)/labdns.log}
CONFIG=${CONFIG:-}

SERVICE_NAME=${SERVICE_NAME:-labdns}
# install mode: user|system (system requires sudo/root)
SERVICE_MODE=${SERVICE_MODE:-user}

cmd_exists() { command -v "$1" >/dev/null 2>&1; }

log() { printf '%s\n' "$*"; }
err() { printf 'Error: %s\n' "$*" >&2; }

is_running() {
  # returns 0 if running
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(sed -n '1p' "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

wait_for_stop() {
  local timeout=${1:-10}
  local i=0
  while is_running; do
    sleep 0.5
    i=$((i+1))
    if (( i >= timeout*2 )); then
      return 1
    fi
  done
  return 0
}

build_start_cmd() {
  local -a cmd=(labdns)
  if [[ -n "$CONFIG" ]]; then
    cmd+=("--config" "$CONFIG")
  fi
  cmd+=(start "--daemon" "--pid-file" "$PID_FILE" "--log-file" "$LOG_FILE" "--interface" "$INTERFACE" "--port" "$PORT")
  if [[ -n "$ZONEFILE" ]]; then
    cmd+=("--zonefile" "$ZONEFILE")
  else
    cmd+=("--zones-dir" "$ZONES_DIR")
  fi
  printf '%q ' "${cmd[@]}"
}

start() {
  if ! cmd_exists labdns; then err "'labdns' command not found in PATH"; exit 127; fi
  if is_running; then
    log "Already running (PID $(cat "$PID_FILE"))"
    return 0
  fi
  mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$LOG_FILE")"
  local cmd
  cmd=$(build_start_cmd)
  log "Starting: $cmd"
  # shellcheck disable=SC2086
  eval $cmd || { err "Failed to start"; exit 1; }
  # Give it a moment to write PID
  sleep 0.3
  if is_running; then
    log "Started. PID $(cat "$PID_FILE")"
  else
    err "Start command completed but process not detected. Check $LOG_FILE"
    exit 1
  fi
}

stop() {
  if ! is_running; then
    log "Not running"
    return 0
  fi
  local pid; pid=$(cat "$PID_FILE" 2>/dev/null || true)
  if [[ -z "$pid" ]]; then err "PID file empty: $PID_FILE"; exit 1; fi
  log "Stopping PID $pid"
  if kill -TERM "$pid" 2>/dev/null; then
    if wait_for_stop 10; then
      log "Stopped"
    else
      err "Timed out waiting for stop; trying SIGKILL"
      kill -KILL "$pid" 2>/dev/null || true
      wait_for_stop 3 || true
    fi
  else
    err "Failed to signal PID $pid"
    exit 1
  fi
}

status() {
  if is_running; then
    local pid; pid=$(cat "$PID_FILE" 2>/dev/null || true)
    log "Running (PID $pid)"
    return 0
  fi
  log "Not running"
  return 3
}

restart() {
  stop || true
  start
}

install_service() {
  if ! cmd_exists systemctl; then err "systemctl not found; cannot install service"; exit 1; fi
  local mode=${1:-$SERVICE_MODE}
  local wd; wd=$(pwd)
  local unit="[Unit]\nDescription=labDNS server\nAfter=network.target\n\n[Service]\nWorkingDirectory=${wd}\nExecStart=labdns start --zones-dir ${ZONES_DIR@Q} --interface ${INTERFACE@Q} --port ${PORT} --no-daemon --no-write-pid\nExecReload=/bin/kill -HUP $MAINPID\nRestart=on-failure\n\n[Install]\nWantedBy=default.target\n"

  if [[ "$mode" == "system" ]]; then
    local path="/etc/systemd/system/${SERVICE_NAME}.service"
    log "Installing system service to $path (requires sudo)"
    printf "%b" "$unit" | sudo tee "$path" >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable --now "$SERVICE_NAME.service"
    log "Installed and started system service '$SERVICE_NAME'"
  else
    local udir="$HOME/.config/systemd/user"
    mkdir -p "$udir"
    local path="$udir/${SERVICE_NAME}.service"
    printf "%b" "$unit" > "$path"
    systemctl --user daemon-reload
    systemctl --user enable --now "$SERVICE_NAME.service"
    log "Installed and started user service '$SERVICE_NAME'"
    log "Tip: to see logs: journalctl --user -u ${SERVICE_NAME} -f"
  fi
}

remove_service() {
  if ! cmd_exists systemctl; then err "systemctl not found"; exit 1; fi
  local mode=${1:-$SERVICE_MODE}
  if [[ "$mode" == "system" ]]; then
    sudo systemctl disable --now "$SERVICE_NAME.service" || true
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    log "Removed system service '$SERVICE_NAME'"
  else
    systemctl --user disable --now "$SERVICE_NAME.service" || true
    rm -f "$HOME/.config/systemd/user/${SERVICE_NAME}.service"
    systemctl --user daemon-reload || true
    log "Removed user service '$SERVICE_NAME'"
  fi
}

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  start               Start labdns (daemonized)
  stop                Stop labdns (SIGTERM)
  restart             Restart labdns
  status              Show running status
  reload              Send SIGHUP to trigger hot reload
  logs                Tail the log file (or journal)
  install [user|system]
                      Install as a systemd service (default: user)
  remove [user|system]
                      Remove the systemd service (default: user)

Environment variables:
  INTERFACE (default: ${INTERFACE})
  PORT      (default: ${PORT})
  ZONES_DIR (default: ${ZONES_DIR})
  ZONEFILE  (default: empty; if set, overrides ZONES_DIR)
  PID_FILE  (default: ${PID_FILE})
  LOG_FILE  (default: ${LOG_FILE})
  CONFIG    (optional: path to labdns.ini)
  SERVICE_NAME (default: ${SERVICE_NAME})
  SERVICE_MODE (default: ${SERVICE_MODE})

Examples:
  ZONES_DIR=./zones INTERFACE=0.0.0.0 PORT=5353 ./labdns.sh start
  ./labdns.sh install           # user service
  SERVICE_MODE=system ./labdns.sh install  # system service (sudo)
EOF
}

reload_cmd() {
  # Prefer PID-based reload if running under this script
  if is_running; then
    if cmd_exists labdns; then
      labdns reload --pid-file "$PID_FILE" && { log "Sent SIGHUP via labdns CLI"; return 0; }
    fi
    # Fallback: send signal directly
    local pid; pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if [[ -n "$pid" ]] && kill -HUP "$pid" 2>/dev/null; then
      log "Sent SIGHUP to PID $pid"
      return 0
    fi
  fi
  # Try systemd reload if service exists
  if cmd_exists systemctl; then
    if [[ "${SERVICE_MODE}" == "system" ]]; then
      systemctl reload "${SERVICE_NAME}.service" && { log "Reloaded system service ${SERVICE_NAME}"; return 0; } || true
    else
      systemctl --user reload "${SERVICE_NAME}.service" && { log "Reloaded user service ${SERVICE_NAME}"; return 0; } || true
    fi
  fi
  err "Could not reload: no running PID and no systemd service found"
  return 1
}

logs_cmd() {
  if [[ -f "$LOG_FILE" ]]; then
    log "Tailing $LOG_FILE (Ctrl-C to stop)"
    tail -F "$LOG_FILE"
    return $?
  fi
  # If no file, try journalctl for service
  if cmd_exists journalctl && cmd_exists systemctl; then
    if [[ "${SERVICE_MODE}" == "system" ]]; then
      journalctl -u "${SERVICE_NAME}.service" -f
    else
      journalctl --user -u "${SERVICE_NAME}.service" -f
    fi
    return $?
  fi
  err "No log file found at $LOG_FILE and journalctl unavailable"
  return 1
}

main() {
  local cmd=${1:-}
  case "${cmd}" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    reload) reload_cmd ;;
    logs|tail-logs) logs_cmd ;;
    install) shift || true; install_service "${1:-}" ;;
    remove) shift || true; remove_service "${1:-}" ;;
    -h|--help|help|"") usage ;;
    *) err "Unknown command: $cmd"; usage; exit 2 ;;
  esac
}

main "$@"
