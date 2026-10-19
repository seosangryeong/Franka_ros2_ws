#!/usr/bin/env bash
# Run once with sudo; applies only to account nuc, not all user services.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Run: sudo bash $0"
  exit 1
fi
if ! id nuc >/dev/null 2>&1; then
  echo 'Account nuc does not exist.' >&2
  exit 1
fi
FRANKA_UID="$(id -u nuc)"
install -d /etc/security/limits.d "/etc/systemd/system/user@${FRANKA_UID}.service.d"
printf '%s\n' 'nuc soft rtprio 99' 'nuc hard rtprio 99' > /etc/security/limits.d/99-franka-nuc.conf
printf '%s\n' '[Service]' 'LimitRTPRIO=99' > "/etc/systemd/system/user@${FRANKA_UID}.service.d/99-franka-rtprio.conf"
systemctl daemon-reload
echo 'Configured rtprio for nuc. Reboot when convenient; then verify: ulimit -r (expected 99).'
