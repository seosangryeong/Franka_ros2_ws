"""Control the Franka Hand directly from the terminal.

  ros2 run fr3_skills gripper --home
  ros2 run fr3_skills gripper --open
  ros2 run fr3_skills gripper --close
  ros2 run fr3_skills gripper --move 0.02
  ros2 run fr3_skills gripper --grasp 0.02 --force 20
"""
import argparse
import sys

import rclpy

from fr3_skills.motion import Fr3Motion, GRIPPER_MAX_WIDTH


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--home', action='store_true', help='homing (required once after power-on)')
    group.add_argument('--open', action='store_true', help=f'move to full open ({GRIPPER_MAX_WIDTH} m)')
    group.add_argument('--close', action='store_true', help='move to width 0')
    group.add_argument('--move', type=float, metavar='WIDTH', help='move to this width [m]')
    group.add_argument('--grasp', type=float, metavar='WIDTH', help='grasp, closing to this width [m]')
    parser.add_argument('--speed', type=float, default=0.1)
    parser.add_argument('--force', type=float, default=20.0, help='grasp force [N]')
    args = parser.parse_args()

    rclpy.init()
    motion = Fr3Motion()
    try:
        if args.home:
            motion.home_gripper()
        elif args.open:
            motion.open_gripper(speed=args.speed)
        elif args.close:
            motion.close_gripper(speed=args.speed)
        elif args.move is not None:
            motion.open_gripper(width=args.move, speed=args.speed)
        elif args.grasp is not None:
            motion.grasp(args.grasp, speed=args.speed, force=args.force)
        print('done.')
    except RuntimeError as e:
        print('stopped:', e)
        sys.exit(1)
    finally:
        motion.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
