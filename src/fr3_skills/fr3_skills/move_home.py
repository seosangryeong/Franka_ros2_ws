"""Move fr3_arm to the 'home' pose from config/poses.yaml.

  ros2 run fr3_skills move_home              # plan only, prints the plan
  ros2 run fr3_skills move_home --execute    # plan, then move (controller must be active)
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
    motion.execute(trajectory)
    print('done. now:', ' '.join(f'{v:+.3f}' for v in motion.current_joints().values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--scaling', type=float, default=0.1)
    args = parser.parse_args()

    rclpy.init()
    motion = Fr3Motion()
    try:
        move_home(motion, args.scaling, args.execute)
    except (RuntimeError, ValueError) as e:
        print('stopped:', e)
        sys.exit(1)
    finally:
        motion.destroy_node()
        rclpy.try_shutdown()
