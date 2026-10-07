"""Fr3Motion: plan with MoveIt, show the plan, execute only when asked."""
import os

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import JointState

JOINTS = [f'fr3_joint{i}' for i in range(1, 8)]
GROUP = 'fr3_arm'
CONTROLLER = 'fr3_arm_controller'
MAX_SCALING = 0.2  # velocity/acceleration scaling cap while testing


def load_pose(name):
    path = os.path.join(get_package_share_directory('fr3_skills'), 'config', 'poses.yaml')
    with open(path) as f:
        values = yaml.safe_load(f)[name]
    return dict(zip(JOINTS, values))


class Fr3Motion(Node):

    def __init__(self):
        super().__init__('fr3_motion')
        self._latest = None
        # Joint order on /franka/joint_states is not 1..7: always map by name.
        self.create_subscription(JointState, '/franka/joint_states', self._on_state, 10)
        self._move = ActionClient(self, MoveGroup, 'move_action')
        self._execute = ActionClient(self, ExecuteTrajectory, 'execute_trajectory')
        self._list = self.create_client(ListControllers, '/controller_manager/list_controllers')

    def _on_state(self, msg):
        self._latest = dict(zip(msg.name, msg.position))

    def current_joints(self, timeout=5.0):
        self._latest = None
        end = self.get_clock().now().nanoseconds + int(timeout * 1e9)
        while rclpy.ok() and self._latest is None:
            if self.get_clock().now().nanoseconds > end:
                raise RuntimeError('no /franka/joint_states (is bringup running?)')
            rclpy.spin_once(self, timeout_sec=0.1)
        return {j: self._latest[j] for j in JOINTS}

    def controller_active(self):
        if not self._list.wait_for_service(timeout_sec=3.0):
            raise RuntimeError('controller_manager not reachable (is bringup running?)')
        future = self._list.call_async(ListControllers.Request())
        rclpy.spin_until_future_complete(self, future)
        for c in future.result().controller:
            if c.name == CONTROLLER:
                return c.state == 'active'
        return False

    def _wait(self, future):
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def plan_to_joints(self, target, scaling=0.1):
        """Return a planned RobotTrajectory to the joint target, or raise."""
        if not 0.0 < scaling <= MAX_SCALING:
            raise ValueError(f'scaling must be in (0, {MAX_SCALING}]')
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = GROUP
        req.num_planning_attempts = 1
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = scaling
        req.max_acceleration_scaling_factor = scaling
        req.start_state.is_diff = True
        c = Constraints()
        for j in JOINTS:
            c.joint_constraints.append(JointConstraint(
                joint_name=j, position=target[j],
                tolerance_above=0.001, tolerance_below=0.001, weight=1.0))
        req.goal_constraints = [c]
        goal.planning_options.plan_only = True

        if not self._move.wait_for_server(timeout_sec=5.0):
            raise RuntimeError('move_group not reachable (is MoveIt running?)')
        handle = self._wait(self._move.send_goal_async(goal))
        result = self._wait(handle.get_result_async()).result
        if result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'planning failed: error_code {result.error_code.val}')
        return result.planned_trajectory

    def describe(self, trajectory, start):
        traj = trajectory.joint_trajectory
        last = traj.points[-1]
        duration = last.time_from_start.sec + last.time_from_start.nanosec * 1e-9
        lines = [f'plan: {len(traj.points)} points, {duration:.2f} s']
        for j in JOINTS:
            k = traj.joint_names.index(j)
            goal = last.positions[k]
            lines.append(f'  {j}: {start[j]:+.3f} -> {goal:+.3f}  (change {goal - start[j]:+.3f} rad)')
        return '\n'.join(lines)

    def execute(self, trajectory):
        if not self.controller_active():
            raise RuntimeError(f'{CONTROLLER} is not active: activate it first')
        if not self._execute.wait_for_server(timeout_sec=5.0):
            raise RuntimeError('execute_trajectory not reachable')
        goal = ExecuteTrajectory.Goal(trajectory=trajectory)
        handle = self._wait(self._execute.send_goal_async(goal))
        code = self._wait(handle.get_result_async()).result.error_code.val
        if code != MoveItErrorCodes.SUCCESS:
            raise RuntimeError(f'execution failed: error_code {code}')
