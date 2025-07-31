#!/bin/bash
set -euo pipefail

# === PARAMETERS ===
IFNAME="wlan0"
CLIENT_SSID="TSI2024"
CLIENT_PSK="TSIRIGA2024"
AP_CON="helmet-ap"
AP_SSID="HelmetMasterAP"
AP_PSK="Helmet1234"

need_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo $0 {on|off|status|restart}"
    exit 1
  fi
}

nm() { sudo nmcli "$@"; }

ensure_client() {
  # Remove duplicate profiles with the same name (gently)
  nm connection delete "$CLIENT_SSID" >/dev/null 2>&1 || true

  # If already connected to the required SSID - good
  if iw dev "$IFNAME" link | grep -q "SSID: $CLIENT_SSID"; then
    return
  fi

  # Connect to client network
  nm dev wifi connect "$CLIENT_SSID" password "$CLIENT_PSK" ifname "$IFNAME"
}

get_client_channel() {
  # Try to get channel number from iw
  local ch
  ch=$(iw dev "$IFNAME" link 2>/dev/null | awk '/channel/ {print $2}' | head -n1 || true)
  # If iw didn't give channel, try through frequency -> channel
  if [[ -z "${ch:-}" ]]; then
    local freq
    freq=$(iw dev "$IFNAME" link 2>/dev/null | awk '/freq:/ {print $2}' | head -n1 || true)
    # Rough conversion of 2.4 GHz to channel
    if [[ -n "${freq:-}" ]]; then
      # Channel ≈ (freq - 2407) / 5, rounded
      ch=$(( (freq - 2407) / 5 ))
    fi
  fi
  echo "${ch:-}"
}

ensure_ap_profile() {
  # Recreate AP profile with correct settings
  nm connection delete "$AP_CON" >/dev/null 2>&1 || true
  nm connection add type wifi ifname "$IFNAME" con-name "$AP_CON" ssid "$AP_SSID"
  nm connection modify "$AP_CON" 802-11-wireless.mode ap
  nm connection modify "$AP_CON" ipv4.method shared
  nm connection modify "$AP_CON" wifi-sec.key-mgmt wpa-psk
  nm connection modify "$AP_CON" wifi-sec.psk "$AP_PSK"

  # Set AP channel = client network channel (if we could determine it)
  local ch
  ch="$(get_client_channel)"
  if [[ -n "$ch" ]]; then
    # Select band by channel number
    if (( ch >= 1 && ch <= 13 )); then
      nm connection modify "$AP_CON" 802-11-wireless.band bg
      nm connection modify "$AP_CON" 802-11-wireless.channel "$ch"
    fi
    # (If client on 5 GHz - for Zero 2W usually AP on 5 GHz is not available, skip)
  fi
}

ap_up() {
  ensure_client
  ensure_ap_profile
  nm connection up "$AP_CON"
}

ap_down() {
  # Just deactivate AP profile (keep client connection)
  nm connection down "$AP_CON" >/dev/null 2>&1 || true
}

show_status() {
  echo "==== nmcli device status ===="
  nm device status
  echo
  echo "==== IP addresses ===="
  ip -4 addr show "$IFNAME" | sed 's/^[ \t]*//'
  echo
  echo "==== Wi-Fi link (iw) ===="
  iw dev "$IFNAME" link || true
  echo
  echo "==== Active connections on $IFNAME ===="
  nm -f GENERAL.CONNECTION,GENERAL.STATE device show "$IFNAME" | sed 's/^[ \t]*//'
}

case "${1:-}" in
  on)
    need_root
    ap_up
    echo "AP '${AP_SSID}' is up and internet is shared through '${CLIENT_SSID}'."
    ;;
  off)
    need_root
    ap_down
    echo "AP '${AP_SSID}' is down. Client connection to '${CLIENT_SSID}' is preserved."
    ;;
  restart)
    need_root
    ap_down
    sleep 1
    ap_up
    echo "AP restarted. Internet sharing from '${CLIENT_SSID}' is enabled."
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: sudo $0 {on|off|status|restart}"
    exit 2
    ;;
esac
