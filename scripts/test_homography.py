"""Click a point on the photo and see its computed robot-frame (x, y).

Sanity check before trusting the homography for real pick targets -- e.g.
click where the robot base actually is in the photo and see if it comes out
close to (0, 0).

  /usr/bin/python3 scripts/test_homography.py path/to/photo.jpg
"""
import json
import sys

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def main():
    if len(sys.argv) != 2:
        print('usage: test_homography.py path/to/photo.jpg')
        sys.exit(1)

    with open('scripts/homography.json') as f:
        H = np.array(json.load(f)['homography'], dtype=np.float32)

    img = Image.open(sys.argv[1])
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.set_title('Click a point to see its robot-frame (x, y)')

    def on_click(event):
        if event.xdata is None:
            return
        px, py = event.xdata, event.ydata
        p = cv2.perspectiveTransform(np.array([[[px, py]]], dtype=np.float32), H)[0][0]
        print(f'pixel ({px:.0f}, {py:.0f}) -> robot (x={p[0]:+.3f}, y={p[1]:+.3f})')
        ax.plot(px, py, 'g+', markersize=15, markeredgewidth=2)
        ax.annotate(f'({p[0]:+.2f},{p[1]:+.2f})', (px, py), color='lime', fontsize=10)
        fig.canvas.draw()

    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()


if __name__ == '__main__':
    main()
