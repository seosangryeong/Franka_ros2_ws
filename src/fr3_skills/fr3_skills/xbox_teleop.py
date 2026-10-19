"""Xbox Joy -> Servo Twist. LB deadman, RB rotation, B software stop."""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from franka_msgs.action import Move, Grasp
from sensor_msgs.msg import Joy, JointState
from geometry_msgs.msg import TwistStamped
from std_srvs.srv import Trigger
from moveit_msgs.srv import GetPlanningScene
from moveit_msgs.msg import PlanningSceneComponents


def xbox_command(axes, buttons, deadzone=0.12):
    if len(axes) < 5 or len(buttons) < 6:
        return None
    if not all(math.isfinite(v) and abs(v) <= 1.01 for v in axes):
        return None
    result = [0.0] * 6
    if not buttons[4] or buttons[1]:
        return result
    def axis(index):
        value = axes[index]
        return 0.0 if abs(value) <= deadzone else math.copysign(min(1.0, (abs(value)-deadzone)/(1-deadzone)),value)
    if buttons[5]:
        result[3], result[4], result[5] = axis(0), axis(1), axis(3)
    else:
        result[0], result[1], result[2], result[5] = axis(1), axis(0), axis(4), axis(3)
    for offset in (0, 3):
        norm = math.sqrt(sum(v*v for v in result[offset:offset+3]))
        if norm > 1.0:
            result[offset:offset+3] = [v/norm for v in result[offset:offset+3]]
    return result


def slew_command(previous, target, max_delta):
    """Limit each linear/angular vector change; units are normalized per tick."""
    result = list(previous)
    for offset in (0, 3):
        delta = [target[i]-previous[i] for i in range(offset, offset+3)]
        norm = math.sqrt(sum(v*v for v in delta))
        fraction = min(1.0, max_delta/norm) if norm else 1.0
        for index in range(3):
            result[offset+index] += delta[index]*fraction
    return result


class GripperToggle:
    """A rising edge toggles the measured hand opening. Never block Servo callbacks."""
    def __init__(self, node):
        self.node = node
        self.a_down = None
        self.last_input = -math.inf
        self.width = None
        self.state_time = -math.inf
        self.completed_at = -math.inf
        self.completed_width = None
        self.busy = False
        self.holding = False
        node.declare_parameter('gripper_force', 20.0)
        self.force = float(node.get_parameter('gripper_force').value)
        if not math.isfinite(self.force) or not 0.0 < self.force <= 70.0:
            raise ValueError('gripper_force must be finite and in (0, 70] N')
        self.grasp_client = ActionClient(node, Grasp, '/franka_gripper/grasp')
        self.client = ActionClient(node, Move, '/franka_gripper/move')
        self.subscription = node.create_subscription(
            JointState, '/franka_gripper/joint_states', self.on_state, 10)

    def on_state(self, msg):
        positions = dict(zip(msg.name, msg.position))
        try:
            width = positions['fr3_finger_joint1'] + positions['fr3_finger_joint2']
        except KeyError:
            return
        if math.isfinite(width) and 0.0 <= width <= 0.1:
            self.width = width
            self.state_time = time.monotonic()

    def on_buttons(self, buttons, now):
        pressed = bool(buttons[0])
        # Held A at startup or after a disconnected input must not trigger motion.
        if now - self.last_input > 0.15:
            self.a_down = None
        self.last_input = now
        rising = self.a_down is False and pressed
        self.a_down = pressed
        if not rising or buttons[1] or self.busy:
            return
        if self.width is None or now - self.state_time > 0.5:
            self.node.get_logger().warning('A ignored: no fresh gripper joint state.')
            return
        width = self.width
        # An action can finish slightly before the corresponding state arrives.
        if self.completed_width is not None and self.state_time <= self.completed_at:
            width = self.completed_width
        # A successful grasp must toggle open even for objects wider than 6 cm.
        target = 0.08 if self.holding or width < 0.06 else 0.0
        client = self.grasp_client if target == 0.0 else self.client
        if not client.server_is_ready():
            self.node.get_logger().warning('A ignored: gripper action server unavailable.')
            return
        if target == 0.0:
            goal = Grasp.Goal(width=0.0, speed=0.03, force=self.force)
            # Unknown object width: accept contact across the hand opening range.
            # This tolerance is not an object-presence or secure-grasp check.
            goal.epsilon.inner = 0.005
            goal.epsilon.outer = 0.08
        else:
            goal = Move.Goal(width=target, speed=0.03)
        self.busy = True
        self.node.get_logger().info(
            f'A: grasping with {self.force:g} N' if target == 0.0 else 'A: opening gripper')
        try:
            future = client.send_goal_async(goal)
            future.add_done_callback(lambda f: self.goal_response(f, target))
        except Exception as error:
            self.failed(error)

    def goal_response(self, future, target):
        try:
            handle = future.result()
            if not handle.accepted:
                self.failed('gripper goal rejected')
                return
            handle.get_result_async().add_done_callback(lambda f: self.finished(f, target))
        except Exception as error:
            self.failed(error)

    def finished(self, future, target):
        try:
            response = future.result()
            if response.status != GoalStatus.STATUS_SUCCEEDED or not response.result.success:
                self.failed(response.result.error or 'gripper action did not succeed')
                return
            self.completed_at = time.monotonic()
            self.completed_width = target
            self.holding = target == 0.0
            self.busy = False
            self.node.get_logger().info(
                'Grasp completed; next A opens (verify object is held).' if self.holding
                else 'Gripper open')
        except Exception as error:
            self.failed(error)

    def failed(self, error):
        self.busy = False
        self.node.get_logger().warning('Gripper: ' + str(error))


class XboxTeleop(Node):
    def __init__(self):
        super().__init__('fr3_xbox_teleop')
        self.declare_parameter('frame_id', 'fr3_link0')
        self.declare_parameter('deadzone', 0.12)
        self.declare_parameter('joy_timeout', 0.15)
        self.declare_parameter('require_table', True)
        self.declare_parameter('command_slew_rate', 1.0)
        self.frame = self.get_parameter('frame_id').value
        self.deadzone = self.get_parameter('deadzone').value
        self.timeout = self.get_parameter('joy_timeout').value
        self.command = [0.0] * 6
        self.output = [0.0] * 6
        self.enabled = False
        self.last_tick = time.monotonic()
        self.slew_rate = self.get_parameter('command_slew_rate').value
        if self.slew_rate <= 0 or not math.isfinite(self.slew_rate):
            raise ValueError('command_slew_rate must be positive and finite')
        self.last_joy = -math.inf
        self.released = False
        self.ready = False
        self.pending = None
        self.start_client = self.create_client(Trigger, '/servo_node/start_servo')
        self.scene_client = self.create_client(GetPlanningScene, '/get_planning_scene')
        self.pub = self.create_publisher(TwistStamped, '/servo_node/delta_twist_cmds', 1)
        self.gripper = GripperToggle(self)
        self.create_subscription(Joy, '/fr3/joy', self.on_joy, 10)
        self.create_timer(0.02, self.tick)
        self.create_timer(1.0, self.start_when_ready)
        self.get_logger().info('Xbox: release LB first; hold LB to move, RB for rotation, B to stop arm input; A toggles gripper (LB not required).')

    def on_joy(self, msg):
        command = xbox_command(msg.axes, msg.buttons, self.deadzone)
        if command is None:
            self.gripper.a_down = None
            self.enabled = False
            self.released = False
            self.command = [0.0] * 6
            return
        self.gripper.on_buttons(msg.buttons, time.monotonic())
        self.enabled = bool(msg.buttons[4]) and not bool(msg.buttons[1])
        if not msg.buttons[4]:
            self.released = True
        if msg.buttons[1]:
            self.released = False
        self.command = command if self.released else [0.0] * 6
        self.last_joy = time.monotonic()

    def tick(self):
        now = time.monotonic()
        dt = min(max(now - self.last_tick, 0.0), 0.02)
        self.last_tick = now
        stale = now - self.last_joy > self.timeout
        if stale or not self.ready:
            self.released = False
        if self.ready and not stale and self.released and self.enabled:
            self.output = slew_command(self.output, self.command, self.slew_rate * dt)
        else:
            # Never delay a deadman/B/timeout stop through the acceleration ramp.
            self.output = [0.0] * 6
        command = self.output
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame
        msg.twist.linear.x, msg.twist.linear.y, msg.twist.linear.z = command[:3]
        msg.twist.angular.x, msg.twist.angular.y, msg.twist.angular.z = command[3:]
        self.pub.publish(msg)

    def start_when_ready(self):
        if self.ready or self.pending is not None:
            return
        if not self.start_client.service_is_ready():
            return
        if self.get_parameter('require_table').value:
            if not self.scene_client.service_is_ready():
                return
            request = GetPlanningScene.Request()
            request.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
            self.pending = self.scene_client.call_async(request)
            self.pending.add_done_callback(self.scene_received)
        else:
            self.start_servo()

    def scene_received(self, future):
        self.pending = None
        try:
            if any(o.id == 'table_floor' for o in future.result().scene.world.collision_objects):
                self.start_servo()
        except Exception as error:
            self.get_logger().warning(str(error))

    def start_servo(self):
        self.pending = self.start_client.call_async(Trigger.Request())
        self.pending.add_done_callback(self.started)

    def started(self, future):
        self.pending = None
        try:
            self.ready = future.result().success
            if self.ready:
                self.released = False
                self.get_logger().info('Servo ready. Release LB, then hold LB while moving a stick.')
        except Exception as error:
            self.get_logger().warning(str(error))


def main():
    rclpy.init()
    node = XboxTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.ready = False
        if rclpy.ok():
            node.tick()
        node.destroy_node()
        rclpy.try_shutdown()
