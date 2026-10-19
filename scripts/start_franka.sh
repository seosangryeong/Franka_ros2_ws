#!/usr/bin/env bash
set -eo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_WORKSPACE="$(cd -- "$PROJECT_DIR/../.." && pwd)"
for argument in "$@"; do
  if [[ "$argument" == 'use_fake_hardware:=false' ]] && (( $(ulimit -r) < 98 )); then
    echo 'Real robot needs rtprio >=98. Run scripts/setup_rtprio.sh with sudo, reboot, and check ulimit -r.' >&2
    exit 1
  fi
done
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
source /opt/ros/humble/setup.bash
source "$ROS_WORKSPACE/install/setup.bash"
exec ros2 launch franka_fr3_moveit_config "${FRANKA_LAUNCH_FILE:-franka_control.launch.py}" "$@"
