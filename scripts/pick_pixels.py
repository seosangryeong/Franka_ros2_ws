"""Click points on an image and print their pixel coordinates.

  /usr/bin/python3 scripts/pick_pixels.py path/to/photo.jpg

Click each point in order (e.g. the 4 table corners); each click prints its
(x, y) pixel coordinate (in the image's native resolution) to the terminal.
Close the window when done.
"""
import sys

import matplotlib.pyplot as plt
from PIL import Image


def main():
    if len(sys.argv) != 2:
        print('usage: pick_pixels.py path/to/photo.jpg')
        sys.exit(1)

    img = Image.open(sys.argv[1])
    fig, ax = plt.subplots()
    ax.imshow(img)
    ax.set_title('Click each point in order; close window when done')

    points = []

    def on_click(event):
        if event.xdata is None:
            return
        x, y = round(event.xdata), round(event.ydata)
        points.append((x, y))
        print(f'point {len(points)}: ({x}, {y})')
        ax.plot(x, y, 'r+', markersize=15, markeredgewidth=2)
        ax.annotate(str(len(points)), (x, y), color='red', fontsize=12)
        fig.canvas.draw()

    fig.canvas.mpl_connect('button_press_event', on_click)
    plt.show()

    print('\nall points:', points)


if __name__ == '__main__':
    main()
