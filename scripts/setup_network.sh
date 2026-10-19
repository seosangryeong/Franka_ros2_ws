#!/usr/bin/env bash
# Use only with a direct Ethernet connection to this FR3's C2 port.
set -euo pipefail
FRANKA_INTERFACE="${1:-}"
if [[ -z "$FRANKA_INTERFACE" ]]; then
  candidates=()
  for device in /sys/class/net/*; do
    [[ -e "$device/device" && ! -d "$device/wireless" ]] || continue
    if [[ "$(cat "$device/carrier" 2>/dev/null || true)" == 1 ]]; then
      candidates+=("${device##*/}")
    fi
  done
  if [[ ${#candidates[@]} -ne 1 ]]; then
    echo 'Connect and power the FR3, or specify its Ethernet interface:'
    echo "  bash $0 enp131s0"
    nmcli -f DEVICE,TYPE,STATE device status
    exit 1
  fi
  FRANKA_INTERFACE="${candidates[0]}"
fi
if [[ "$(nmcli -g GENERAL.TYPE device show "$FRANKA_INTERFACE")" != ethernet ]]; then
  echo 'Expected an Ethernet interface.' >&2
  exit 1
fi
if ! nmcli -g connection.id connection show franka-direct >/dev/null 2>&1; then
  nmcli connection add type ethernet ifname "$FRANKA_INTERFACE" con-name franka-direct
fi
nmcli connection modify franka-direct connection.interface-name "$FRANKA_INTERFACE" \
  ipv4.method manual ipv4.addresses 172.16.0.10/24 ipv4.gateway '' ipv4.dns '' \
  ipv4.never-default yes ipv6.method disabled connection.autoconnect yes \
  connection.autoconnect-priority 100
nmcli connection up franka-direct
ip route get 172.16.0.2
ping -n -c 3 -W 2 172.16.0.2
