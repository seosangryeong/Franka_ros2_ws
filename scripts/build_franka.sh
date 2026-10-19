#!/usr/bin/env bash
set -eo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_WORKSPACE="$(cd -- "$PROJECT_DIR/../.." && pwd)"
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
source /opt/ros/humble/setup.bash
cd "$ROS_WORKSPACE"
colcon build --symlink-install --parallel-workers 3 \
  --packages-select libfranka franka_description franka_msgs franka_hardware \
  franka_semantic_components franka_robot_state_broadcaster franka_gripper \
  franka_bringup franka_fr3_moveit_config fr3_skills dual_franka_description \
  olv_module_descriptions \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DBUILD_TESTS=OFF -DBUILD_EXAMPLES=OFF \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 -DPython3_EXECUTABLE=/usr/bin/python3
