"""Load the saved table collision box without issuing motion commands."""
import time
import rclpy
from fr3_skills.motion import Fr3Motion


def main():
    rclpy.init()
    node = Fr3Motion()
    try:
        deadline = time.monotonic() + 60.0
        while not node._apply_scene.wait_for_service(timeout_sec=1.0):
            if time.monotonic() >= deadline:
                raise RuntimeError('MoveIt planning-scene service not available after 60 seconds')
        node.ensure_table_collision()
        node.get_logger().info('Saved table_floor collision box loaded; verify it against the real setup.')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
