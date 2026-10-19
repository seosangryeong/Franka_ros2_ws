#!/usr/bin/env bash
set -eo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${CYCLONEDDS_URI:-}" ]]; then
  export CYCLONEDDS_URI='<CycloneDDS><Domain id="any"><Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>100</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
fi
export FRANKA_LAUNCH_FILE=xbox_teleop.launch.py
exec "$SCRIPT_DIR/start_franka.sh" "$@"
