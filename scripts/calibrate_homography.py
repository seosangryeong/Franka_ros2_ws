"""Compute and save the pixel-to-robot-frame homography for the fixed table camera.

Table corners (real, in fr3_link0 frame, from the calibrated table model):
  x=0   is the edge flush with the robot base (back edge)
  x=0.6 is the far edge (table depth)
  y=-0.3 .. +0.3 is the table width, centered

Pixel corners were picked by hand from a photo with scripts/pick_pixels.py,
clicking in this order: front-left, front-right, back-right, back-left.
ASSUMPTION (needs verification): the camera looks from the table's far (+X)
side back toward the robot, so image-left = robot -Y, image-right = robot +Y.
Verify by sending the robot to a known +y pose and checking which side of the
image it appears on; flip the y signs below if it's backwards.

  /usr/bin/python3 scripts/calibrate_homography.py
"""
import json

import cv2
import numpy as np

# (pixel_x, pixel_y) -> (robot_x, robot_y), one row per corner, same order.
PIXEL_POINTS = np.array([
    [138, 1376],   # front-left
    [2356, 2080],  # front-right
    [2927, 949],   # back-right
    [1466, 731],   # back-left
], dtype=np.float32)

ROBOT_POINTS = np.array([
    [0.6, -0.3],  # front-left  -> far edge, -Y side
    [0.6, 0.3],   # front-right -> far edge, +Y side
    [0.0, 0.3],   # back-right  -> near edge (robot side), +Y side
    [0.0, -0.3],  # back-left   -> near edge (robot side), -Y side
], dtype=np.float32)

OUT_PATH = 'scripts/homography.json'


def main():
    H, mask = cv2.findHomography(PIXEL_POINTS, ROBOT_POINTS)
    print('homography matrix:')
    print(H)

    # Sanity check: re-project each pixel corner through H and compare to the
    # intended robot coordinate -- should match closely (it's an exact fit
    # for 4 points, so this just catches typos/mistakes).
    print('\nsanity check (reprojected vs intended):')
    for (px, py), (rx, ry) in zip(PIXEL_POINTS, ROBOT_POINTS):
        p = cv2.perspectiveTransform(np.array([[[px, py]]], dtype=np.float32), H)[0][0]
        print(f'  pixel ({px:.0f},{py:.0f}) -> ({p[0]:+.3f},{p[1]:+.3f})  intended ({rx:+.3f},{ry:+.3f})')

    with open(OUT_PATH, 'w') as f:
        json.dump({'homography': H.tolist()}, f, indent=2)
    print(f'\nsaved to {OUT_PATH}')


if __name__ == '__main__':
    main()
