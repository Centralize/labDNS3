#!/usr/bin/env bash
# labdns-gui.sh - simple GUI wrapper for labDNS using zenity/yad
# Requires: zenity or yad available in PATH

set -euo pipefail

APP_NAME="labdns"
APP_TITLE="labDNS GUI"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/labdns"
GUI_CFG="$CONFIG_DIR/gui.conf"

detect_backend() {
  if command -v yad >/dev/null 2>&1; then echo "yad"; return; fi
  if command -v zenity >/dev/null 2>&1; then echo "zenity"; return; fi
  echo ""; return
}

BACKEND=$(detect_backend)
if [[ -z "$BACKEND" ]]; then
  echo "Error: neither 'yad' nor 'zenity' is installed." >&2
  exit 1
fi

ensure_cfg() {
  mkdir -p "$CONFIG_DIR"
  if [[ ! -f "$GUI_CFG" ]]; then
    cat >"$GUI_CFG" <<EOF
ZONES_DIR="$(pwd)/zones"
ZONEFILE=""
INTERFACE="127.0.0.1"
PORT="5353"
PID_FILE="$(pwd)/labdns.pid"
LOG_FILE="$(pwd)/labdns.log"
EOF
  fi
}

load_cfg() {
  ensure_cfg
  # shellcheck disable=SC1090
  . "$GUI_CFG"
}

save_cfg() {
  cat >"$GUI_CFG" <<EOF
ZONES_DIR=${ZONES_DIR@Q}
ZONEFILE=${ZONEFILE@Q}
INTERFACE=${INTERFACE@Q}
PORT=${PORT@Q}
PID_FILE=${PID_FILE@Q}
LOG_FILE=${LOG_FILE@Q}
EOF
}

dialog_info() {
  local msg="$1"
  if [[ $BACKEND == "yad" ]]; then
    yad --title="$APP_TITLE" --image=dialog-information --text="$msg" --button=OK:0 --center --width=500
  else
    zenity --info --title="$APP_TITLE" --text="$msg"
  fi
}

dialog_error() {
  local msg="$1"
  if [[ $BACKEND == "yad" ]]; then
    yad --title="$APP_TITLE" --image=dialog-error --text="$msg" --button=OK:0 --center --width=500
  else
    zenity --error --title="$APP_TITLE" --text="$msg"
  fi
}

dialog_textinfo() {
  local title="$1"; shift
  local content="$1"; shift || true
  if [[ $BACKEND == "yad" ]]; then
    echo -e "$content" | yad --title="$title" --text-info --width=800 --height=500 --center --button=OK:0
  else
    echo -e "$content" | zenity --text-info --title="$title" --width=800 --height=500
  fi
}

pick_file() {
  local title="$1"; shift
  if [[ $BACKEND == "yad" ]]; then
    yad --file --title="$title" --center --width=800 || true
  else
    zenity --file-selection --title="$title" || true
  fi
}

pick_dir() {
  local title="$1"; shift
  if [[ $BACKEND == "yad" ]]; then
    yad --file --directory --title="$title" --center --width=800 || true
  else
    zenity --file-selection --directory --title="$title" || true
  fi
}

input_text() {
  local title="$1"; shift
  local entry_text="$1"; shift
  local prefill="$1"; shift
  if [[ $BACKEND == "yad" ]]; then
    yad --form --title="$title" --center --separator="|" --field="$entry_text" "$prefill" || true
  else
    zenity --entry --title="$title" --text="$entry_text" --entry-text="$prefill" || true
  fi
}

confirm() {
  local text="$1"; shift
  if [[ $BACKEND == "yad" ]]; then
    yad --question --title="$APP_TITLE" --text="$text" --button=No:1 --button=Yes:0
  else
    zenity --question --title="$APP_TITLE" --text="$text"
  fi
}

run_cmd() {
  local cmd=("$@")
  local out err rc
  out=$("${cmd[@]}" 2>&1) || rc=$?
  rc=${rc:-0}
  echo "$out"
  return $rc
}

action_start() {
  load_cfg
  # Choose source type
  local choice
  if [[ $BACKEND == "yad" ]]; then
    choice=$(yad --list --title="$APP_TITLE" --center --width=400 --height=200 \
      --column="Action" --hide-column=2 --column="value" \
      "Use Zones Directory" "dir" "Use Zonefile" "file" || true)
    choice=$(awk -F'|' '{print $2}' <<<"$choice")
  else
    choice=$(zenity --list --title="$APP_TITLE" --text="Select Source" --column=Action "Use Zones Directory" "Use Zonefile" || true)
    if [[ "$choice" == "Use Zones Directory" ]]; then choice="dir"; else choice="file"; fi
  fi
  [[ -z "$choice" ]] && return

  if [[ "$choice" == "dir" ]]; then
    local d=$(pick_dir "Select zones directory")
    [[ -n "$d" ]] && ZONES_DIR="$d" && ZONEFILE=""
  else
    local f=$(pick_file "Select zonefile")
    [[ -n "$f" ]] && ZONEFILE="$f" && ZONES_DIR=""
  fi

  local iface=$(input_text "$APP_TITLE" "Interface" "$INTERFACE")
  local port=$(input_text "$APP_TITLE" "Port" "$PORT")
  local pidf=$(input_text "$APP_TITLE" "PID file" "$PID_FILE")
  local logf=$(input_text "$APP_TITLE" "Log file" "$LOG_FILE")
  [[ -n "$iface" ]] && INTERFACE="$iface"
  [[ -n "$port" ]] && PORT="$port"
  [[ -n "$pidf" ]] && PID_FILE="$pidf"
  [[ -n "$logf" ]] && LOG_FILE="$logf"
  save_cfg

  # Build command
  local cmd=("$APP_NAME" "start" "--daemon" "--pid-file" "$PID_FILE" "--log-file" "$LOG_FILE" "--interface" "$INTERFACE" "--port" "$PORT")
  if [[ -n "$ZONES_DIR" ]]; then
    cmd+=("--zones-dir" "$ZONES_DIR")
  elif [[ -n "$ZONEFILE" ]]; then
    cmd+=("--zonefile" "$ZONEFILE")
  fi
  local out
  out=$(run_cmd "${cmd[@]}")
  if [[ $? -eq 0 ]]; then
    dialog_info "Server started.\nPID file: $PID_FILE\nLog: $LOG_FILE"
  else
    dialog_error "Failed to start server:\n$out"
  fi
}

action_check() {
  load_cfg
  local path
  path=$(pick_file "Select zonefile or choose Cancel to pick a directory")
  if [[ -z "$path" ]]; then
    path=$(pick_dir "Select zones directory")
  fi
  [[ -z "$path" ]] && return
  local out
  out=$(run_cmd "$APP_NAME" check "$path")
  if [[ $? -eq 0 ]]; then
    dialog_info "$out"
  else
    dialog_error "$out"
  fi
}

action_reload() {
  load_cfg
  local out
  out=$(run_cmd "$APP_NAME" reload --pid-file "$PID_FILE")
  if [[ $? -eq 0 ]]; then
    dialog_info "$out"
  else
    dialog_error "$out"
  fi
}

action_stop() {
  load_cfg
  if ! [[ -f "$PID_FILE" ]]; then
    dialog_error "PID file not found: $PID_FILE"
    return
  fi
  local pid; pid=$(cat "$PID_FILE" 2>/dev/null || true)
  if [[ -z "$pid" ]]; then
    dialog_error "PID file empty: $PID_FILE"
    return
  fi
  if confirm "Send SIGTERM to PID $pid?"; then
    if kill -TERM "$pid" 2>/dev/null; then
      dialog_info "Sent SIGTERM to $pid"
    else
      dialog_error "Failed to signal $pid"
    fi
  fi
}

action_logs() {
  load_cfg
  local content
  if [[ -f "$LOG_FILE" ]]; then
    content=$(tail -n 200 "$LOG_FILE" 2>&1 || true)
  else
    content="Log file not found: $LOG_FILE"
  fi
  dialog_textinfo "$APP_TITLE - Logs" "$content"
}

action_settings() {
  load_cfg
  local d1=$(pick_dir "Default zones directory (Cancel to keep)")
  [[ -n "$d1" ]] && ZONES_DIR="$d1"
  local f1=$(pick_file "Default zonefile (Cancel to keep)")
  [[ -n "$f1" ]] && ZONEFILE="$f1"
  local iface=$(input_text "$APP_TITLE" "Default interface" "$INTERFACE")
  [[ -n "$iface" ]] && INTERFACE="$iface"
  local port=$(input_text "$APP_TITLE" "Default port" "$PORT")
  [[ -n "$port" ]] && PORT="$port"
  local pidf=$(input_text "$APP_TITLE" "Default PID file" "$PID_FILE")
  [[ -n "$pidf" ]] && PID_FILE="$pidf"
  local logf=$(input_text "$APP_TITLE" "Default log file" "$LOG_FILE")
  [[ -n "$logf" ]] && LOG_FILE="$logf"
  save_cfg
  dialog_info "Settings saved"
}

main_menu() {
  while true; do
    local choice
    if [[ $BACKEND == "yad" ]]; then
      choice=$(yad --list --title="$APP_TITLE" --center --width=500 --height=320 \
        --column="Action" \
        "Start Server" \
        "Create New Zone" \
        "Add Record" \
        "Remove Record" \
        "Check Zonefile/Dir" \
        "Reload Server" \
        "View Logs" \
        "Stop Server" \
        "Settings" \
        "Quit" || true)
    else
      choice=$(zenity --list --title="$APP_TITLE" --text="Choose an action" --column=Action \
        "Start Server" "Create New Zone" "Add Record" "Remove Record" "Check Zonefile/Dir" "Reload Server" "View Logs" "Stop Server" "Settings" "Quit" || true)
    fi
    case "$choice" in
      "Start Server") action_start ;;
      "Create New Zone") action_new_zone ;;
      "Add Record") action_add_record ;;
      "Remove Record") action_remove_record ;;
      "Check Zonefile/Dir") action_check ;;
      "Reload Server") action_reload ;;
      "View Logs") action_logs ;;
      "Stop Server") action_stop ;;
      "Settings") action_settings ;;
      "Quit"|"") break ;;
      *) : ;;
    esac
  done
}

# ----- Zone management helpers -----

fqdn_dot() {
  local name="$1"
  [[ -z "$name" ]] && echo "" && return
  if [[ "$name" == *. ]]; then echo "$name"; else echo "$name."; fi
}

action_new_zone() {
  load_cfg
  local origin ttl ns hostmaster serial outfile
  origin=$(input_text "$APP_TITLE" "Zone origin (e.g. example.test.)" "example.test.")
  [[ -z "$origin" ]] && return
  origin=$(fqdn_dot "$origin")
  ttl=$(input_text "$APP_TITLE" "Default TTL" "300")
  [[ -z "$ttl" ]] && ttl=300
  ns=$(input_text "$APP_TITLE" "Primary NS (fqdn)" "ns1.${origin}")
  ns=$(fqdn_dot "$ns")
  hostmaster=$(input_text "$APP_TITLE" "Hostmaster email (user.example.)" "hostmaster.${origin}")
  hostmaster=$(fqdn_dot "$hostmaster")
  serial=$(date +%Y%m%d01)
  outfile=$(pick_file "Choose path to save zone (new file)")
  [[ -z "$outfile" ]] && return
  if [[ -e "$outfile" ]]; then
    if ! confirm "File exists. Overwrite?"; then return; fi
  fi
  cat >"$outfile" <<EOF
$ORIGIN ${origin}
$TTL ${ttl}
@   IN SOA ${ns} ${hostmaster} (
        ${serial} ; serial
        3600       ; refresh
        900        ; retry
        1209600    ; expire
        ${ttl}     ; minimum
)
    IN NS  ${ns}
EOF
  dialog_info "Created new zone at ${outfile}"
}

ask_record_type() {
  if [[ $BACKEND == "yad" ]]; then
    yad --list --title="$APP_TITLE" --center --width=400 --height=320 \
      --column="Type" A AAAA CNAME MX TXT SRV CAA NS PTR || true
  else
    zenity --list --title="$APP_TITLE" --text="Select record type" --column=Type \
      A AAAA CNAME MX TXT SRV CAA NS PTR || true
  fi
}

select_zonefile() {
  load_cfg
  if [[ -n "$ZONEFILE" ]]; then echo "$ZONEFILE"; return; fi
  if [[ -n "$ZONES_DIR" && -d "$ZONES_DIR" ]]; then
    pick_file "Select zonefile in ${ZONES_DIR}"
  else
    pick_file "Select zonefile"
  fi
}

action_add_record() {
  local zf name type ttl line
  zf=$(select_zonefile)
  [[ -z "$zf" ]] && return
  name=$(input_text "$APP_TITLE" "Record name (relative or FQDN)" "www")
  [[ -z "$name" ]] && return
  type=$(ask_record_type)
  [[ -z "$type" ]] && return
  ttl=$(input_text "$APP_TITLE" "TTL (optional)" "")

  case "$type" in
    A|AAAA)
      local addr; addr=$(input_text "$APP_TITLE" "Address" "")
      [[ -z "$addr" ]] && { dialog_error "Address required"; return; }
      line="$name ${ttl:+$ttl }IN $type $addr"
      ;;
    CNAME|NS|PTR)
      local target; target=$(input_text "$APP_TITLE" "Target (fqdn)" "")
      [[ -z "$target" ]] && { dialog_error "Target required"; return; }
      target=$(fqdn_dot "$target")
      line="$name ${ttl:+$ttl }IN $type $target"
      ;;
    MX)
      local pref exch; pref=$(input_text "$APP_TITLE" "Preference" "10"); exch=$(input_text "$APP_TITLE" "Exchange (fqdn)" "")
      [[ -z "$exch" ]] && { dialog_error "Exchange required"; return; }
      exch=$(fqdn_dot "$exch")
      line="$name ${ttl:+$ttl }IN MX $pref $exch"
      ;;
    TXT)
      local text; text=$(input_text "$APP_TITLE" "TXT text (use | to separate chunks)" "")
      [[ -z "$text" ]] && { dialog_error "TXT text required"; return; }
      IFS='|' read -r -a parts <<<"$text"
      local quoted=""; for p in "${parts[@]}"; do quoted+=" \"${p}\""; done
      line="$name ${ttl:+$ttl }IN TXT${quoted}"
      ;;
    SRV)
      local pr wt port tgt; pr=$(input_text "$APP_TITLE" "Priority" "10"); wt=$(input_text "$APP_TITLE" "Weight" "5"); port=$(input_text "$APP_TITLE" "Port" "5060"); tgt=$(input_text "$APP_TITLE" "Target (fqdn)" "")
      [[ -z "$tgt" ]] && { dialog_error "Target required"; return; }
      tgt=$(fqdn_dot "$tgt")
      line="$name ${ttl:+$ttl }IN SRV $pr $wt $port $tgt"
      ;;
    CAA)
      local flags tag value; flags=$(input_text "$APP_TITLE" "Flags" "0"); tag=$(input_text "$APP_TITLE" "Tag (issue/iodef)" "issue"); value=$(input_text "$APP_TITLE" "Value" "letsencrypt.org")
      line="$name ${ttl:+$ttl }IN CAA $flags $tag \"$value\""
      ;;
    *)
      dialog_error "Type not supported by GUI."
      return
      ;;
  esac

  echo "$line" >>"$zf"
  dialog_info "Added: $line\n-> $zf"
  if confirm "Reload server now?"; then
    action_reload
  fi
}

action_remove_record() {
  local zf name type
  zf=$(select_zonefile)
  [[ -z "$zf" ]] && return
  name=$(input_text "$APP_TITLE" "Record name to remove" "www")
  [[ -z "$name" ]] && return
  type=$(ask_record_type)
  [[ -z "$type" ]] && return
  # sed pattern: ^\s*name(\s+TTL)?\s+IN\s+TYPE\b ...
  local pat="^\\s*${name}((\\s+)[0-9]+)?(\\s+)IN(\\s+)${type}\\b"
  if confirm "Remove lines matching: $name IN $type from $(basename "$zf")?"; then
    if sed -En "$pat" "$zf" | grep -q .; then
      cp "$zf" "${zf}.bak"
      sed -E -i "${pat}/d" "$zf"
      dialog_info "Removed matching records. Backup saved: ${zf}.bak"
      if confirm "Reload server now?"; then
        action_reload
      fi
    else
      dialog_error "No matching lines found."
    fi
  fi
}

# Invoke menu after all functions are defined
main_menu
