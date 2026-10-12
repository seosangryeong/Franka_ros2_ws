"""Detect the largest blue blob in a photo, convert its center to robot (x, y).

  /usr/bin/python3 scripts/detect_blue.py path/to/photo.jpg [--save out.jpg]

Prints the detected pixel centroid and, if scripts/homography.json exists,
the corresponding robot-frame (x, y). With --save, writes an annotated copy
(mask overlay + centroid marker) so you can check the detection visually.
"""
import argparse
import json
import os

import cv2
import numpy as np

# Generous range for a light/pastel blue plush toy; narrow this down once we
# see how well it isolates the object vs. the gray table/floor background.
HSV_LOWER = np.array([90, 40, 80])
HSV_UPPER = np.array([130, 255, 255])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('photo')
    parser.add_argument('--save', default=None, help='save an annotated copy here')
    args = parser.parse_args()

    img = cv2.imread(args.photo)
    if img is None:
        raise SystemExit(f'could not read {args.photo}')
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print('no blue blob found -- check HSV_LOWER/HSV_UPPER range')
        return
    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    M = cv2.moments(largest)
    px, py = M['m10'] / M['m00'], M['m01'] / M['m00']
    print(f'blob area: {area:.0f} px, centroid: ({px:.0f}, {py:.0f})')

    if os.path.exists('scripts/homography.json'):
        with open('scripts/homography.json') as f:
            H = np.array(json.load(f)['homography'], dtype=np.float32)
        p = cv2.perspectiveTransform(np.array([[[px, py]]], dtype=np.float32), H)[0][0]
        print(f'robot frame: x={p[0]:+.3f}, y={p[1]:+.3f}')

    if args.save:
        overlay = img.copy()
        overlay[mask > 0] = (0, 0, 255)
        blended = cv2.addWeighted(img, 0.6, overlay, 0.4, 0)
        cv2.drawContours(blended, [largest], -1, (0, 255, 0), 3)
        cv2.circle(blended, (int(px), int(py)), 15, (0, 255, 255), -1)
        cv2.imwrite(args.save, blended)
        print(f'saved annotated image to {args.save}')


if __name__ == '__main__':
    main()
