"""Capture a photo, detect the largest blue blob, publish its robot-frame pose.

Needs scripts/homography.json (see scripts/calibrate_homography.py) and a
camera at --device. Publishes once and exits by default.

  ros2 run fr3_skills object_pose_publisher
  ros2 run fr3_skills object_pose_publisher --z 0.05 --save /tmp/check.jpg
"""
import argparse
import json
import time

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node

from fr3_skills.motion import BASE_FRAME

# Same range as scripts/detect_blue.py -- keep these in sync, or refactor into
# a shared module once this is doing more than one color/object.
HSV_LOWER = np.array([90, 40, 80])
HSV_UPPER = np.array([130, 255, 255])
# Relative to the current directory -- run this from ~/franka_ros2_ws (same as
# every other command in this project). Override with --homography if needed.
HOMOGRAPHY_PATH = 'scripts/homography.json'


def detect(frame, save_path=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    M = cv2.moments(largest)
    if M['m00'] == 0:
        return None
    px, py = M['m10'] / M['m00'], M['m01'] / M['m00']

    if save_path:
        overlay = frame.copy()
        overlay[mask > 0] = (0, 0, 255)
        blended = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)
        cv2.drawContours(blended, [largest], -1, (0, 255, 0), 3)
        cv2.circle(blended, (int(px), int(py)), 15, (0, 255, 255), -1)
        cv2.imwrite(save_path, blended)

    return px, py


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--topic', default='/object_pose')
    parser.add_argument('--z', type=float, default=0.05, help='assumed object height [m]')
    parser.add_argument('--save', default=None, help='save an annotated photo here')
    parser.add_argument('--warmup', type=float, default=1.0,
                         help='seconds to let the camera auto-exposure settle')
    parser.add_argument('--homography', default=HOMOGRAPHY_PATH)
    parser.add_argument('--width', type=int, default=3840,
                         help='must match the resolution the homography was calibrated at')
    parser.add_argument('--height', type=int, default=2160)
    args = parser.parse_args()

    with open(args.homography) as f:
        H = np.array(json.load(f)['homography'], dtype=np.float32)

    cap = cv2.VideoCapture(args.device)
    if not cap.isOpened():
        raise SystemExit(f'could not open camera /dev/video{args.device}')
    # VideoCapture defaults to the YUYV format, which this camera only
    # supports up to 640x480 -- silently breaking the homography (calibrated
    # against the camera's native resolution via photos taken through
    # cheese). 3840x2160 only exists under MJPG (v4l2-ctl --list-formats-ext).
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if (actual_w, actual_h) != (args.width, args.height):
        print(f'warning: camera gave {actual_w:.0f}x{actual_h:.0f}, '
              f'not the requested {args.width}x{args.height} -- '
              'homography will be wrong unless it was calibrated at this size')
    time.sleep(args.warmup)
    # The very first frame after (re)opening at this format/resolution comes
    # back black (measured: frame 0 mean brightness 0.0, frame 1+ ~131), and
    # auto-exposure/auto-focus can still be settling for a few more frames
    # after that (detection was flaky run-to-run until this retry loop was
    # added) -- discard some, then try detection on each of several more
    # frames instead of just the first one that reads.
    for _ in range(5):
        cap.read()
    result = None
    for _ in range(10):
        ok, frame = cap.read()
        if not ok:
            continue
        result = detect(frame, args.save)  # save overwrites each try; final one sticks
        if result is not None:
            break
    cap.release()
    if result is None:
        if args.save:
            cv2.imwrite(args.save, frame)
        raise SystemExit('no blue blob found in 10 frames -- check lighting/HSV range'
                          + (f' (last frame saved to {args.save})' if args.save else ''))
    px, py = result
    p = cv2.perspectiveTransform(np.array([[[px, py]]], dtype=np.float32), H)[0][0]
    print(f'pixel ({px:.0f}, {py:.0f}) -> robot (x={p[0]:+.3f}, y={p[1]:+.3f})')

    rclpy.init()
    node = Node('object_pose_publisher')
    pub = node.create_publisher(PoseStamped, args.topic, 10)
    # A one-shot publish() right after creating the publisher can race DDS
    # discovery -- if no subscriber is matched yet, the message is silently
    # dropped (no error). Wait for an actual subscriber (e.g. pose_listener)
    # instead of a fixed sleep.
    deadline = time.time() + 5.0
    while pub.get_subscription_count() == 0 and time.time() < deadline:
        time.sleep(0.1)
    if pub.get_subscription_count() == 0:
        print(f'warning: no subscriber on {args.topic} after 5s -- '
              'is pose_listener running? publishing anyway.')

    msg = PoseStamped()
    msg.header.frame_id = BASE_FRAME
    msg.pose.position.x = float(p[0])
    msg.pose.position.y = float(p[1])
    msg.pose.position.z = args.z
    msg.pose.orientation.x = 1.0  # pointing straight down, same as pick_place.py
    msg.pose.orientation.w = 0.0
    pub.publish(msg)
    print(f'published to {args.topic} ({pub.get_subscription_count()} subscriber(s))')

    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
