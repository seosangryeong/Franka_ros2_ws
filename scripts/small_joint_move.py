#!/usr/bin/env python3
"""Plan (and optionally execute) a small single-joint move of fr3_arm via MoveIt.

Default is plan only. Examples:
  python3 scripts/small_joint_move.py --joint fr3_joint7 --delta 0.01
  python3 scripts/small_joint_move.py --joint fr3_joint7 --delta 0.01 --execute
--execute requires fr3_arm_controller to be active.
"""
import argparse
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes

JOINTS = [f'fr3_joint{i}' for i in range(1, 8)]
MAX_DELTA = 0.05  # rad, hard cap for this test script


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--joint', default='fr3_joint7', choices=JOINTS)
    parser.add_argument('--delta', type=float, default=0.01)
    parser.add_argument('--scaling', type=float, default=0.1)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if abs(args.delta) > MAX_DELTA or not 0.0 < args.scaling <= 0.1:
        sys.exit(f'refused: |delta| must be <= {MAX_DELTA} rad and scaling in (0, 0.1]')

    rclpy.init()
    node = Node('small_joint_move')

    # Joint order on /franka/joint_states is not 1..7: always map by name.
    current = {}

    def on_state(msg):
        if not current:
            current.update(dict(zip(msg.name, msg.position)))
    node.create_subscription(JointState, '/franka/joint_states', on_state, 10)
    while rclpy.ok() and not current:
        rclpy.spin_once(node, timeout_sec=0.1)
    start = [current[j] for j in JOINTS]
    target = dict(zip(JOINTS, start))
    target[args.joint] += args.delta

    print('current [rad]:', ' '.join(f'{v:+.4f}' for v in start))
    print(f'target: {args.joint} {current[args.joint]:+.4f} -> {target[args.joint]:+.4f}')

    goal = MoveGroup.Goal()
    req = goal.request
    req.group_name = 'fr3_arm'
    req.num_planning_attempts = 1
    req.allowed_planning_time = 5.0
    req.max_velocity_scaling_factor = args.scaling
    req.max_acceleration_scaling_factor = args.scaling
    req.start_state.is_diff = True
    c = Constraints()
    for j in JOINTS:
        c.joint_constraints.append(JointConstraint(
            joint_name=j, position=target[j],
            tolerance_above=0.001, tolerance_below=0.001, weight=1.0))
    req.goal_constraints = [c]
    goal.planning_options.plan_only = True

    move = ActionClient(node, MoveGroup, 'move_action')
    move.wait_for_server()
    fut = move.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, fut)
    res_fut = fut.result().get_result_async()
    rclpy.spin_until_future_complete(node, res_fut)
    result = res_fut.result().result
    if result.error_code.val != MoveItErrorCodes.SUCCESS:
        sys.exit(f'planning failed: error_code {result.error_code.val}')

    traj = result.planned_trajectory.joint_trajectory
    names = list(traj.joint_names)
    pts = traj.points
    dur = pts[-1].time_from_start.sec + pts[-1].time_from_start.nanosec * 1e-9
    print(f'plan OK: {len(pts)} points, duration {dur:.2f} s')
    for j in JOINTS:
        k = names.index(j)
        vals = [p.positions[k] for p in pts]
        span = max(abs(v - current[j]) for v in vals)
        vmax = max(abs(p.velocities[k]) for p in pts) if pts[0].velocities else 0.0
        print(f'  {j}: max deviation {span:.4f} rad, max vel {vmax:.4f} rad/s')

    if not args.execute:
        print('plan only (not executed)')
        return

    ex = ActionClient(node, ExecuteTrajectory, 'execute_trajectory')
    ex.wait_for_server()
    eg = ExecuteTrajectory.Goal()
    eg.trajectory = result.planned_trajectory
    fut = ex.send_goal_async(eg)
    rclpy.spin_until_future_complete(node, fut)
    res_fut = fut.result().get_result_async()
    rclpy.spin_until_future_complete(node, res_fut)
    code = res_fut.result().result.error_code.val
    print('execute result:', 'SUCCESS' if code == MoveItErrorCodes.SUCCESS else f'error_code {code}')

    current.clear()
    while rclpy.ok() and not current:
        rclpy.spin_once(node, timeout_sec=0.1)
    print('after   [rad]:', ' '.join(f'{current[j]:+.4f}' for j in JOINTS))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
