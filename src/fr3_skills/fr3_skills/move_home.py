"""Move fr3_arm to the 'home' pose from config/poses.yaml, gripper open.

  ros2 run fr3_skills move_home              # plan only, prints the plan
  ros2 run fr3_skills move_home --execute    # plan, then move arm + open gripper --
                                              # activates/deactivates fr3_arm_controller
                                              # itself. Needs bringup with load_gripper:=true.
"""
import argparse
import sys

import rclpy

from fr3_skills.motion import Fr3Motion, load_pose


def move_home(motion, scaling=0.1, execute=False):
    start = motion.current_joints()
    trajectory = motion.plan_to_joints(load_pose('home'), scaling)
    print(motion.describe(trajectory, start))
    if not execute:
        print('plan only (not executed)')
        return
    motion.activate_arm()
    try:
        motion.execute(trajectory)
    finally:
        motion.deactivate_arm()
    motion.open_gripper()
    print('done. now:', ' '.join(f'{v:+.3f}' for v in motion.current_joints().values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--scaling', type=float, default=0.1)
    args = parser.parse_args()

    rclpy.init()
    motion = Fr3Motion()
    try:
        motion.ensure_table_collision()
        move_home(motion, args.scaling, args.execute)
    except (RuntimeError, ValueError) as e:
        print('stopped:', e)
        sys.exit(1)
    finally:
        motion.destroy_node()
        rclpy.try_shutdown()
