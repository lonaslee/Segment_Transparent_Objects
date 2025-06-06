import cv2


from sys import argv
from os import listdir

import numpy as np


def main():
    compareToDir = "demo/imgs"
    if (len(argv) == 2):
        compareToDir = argv[1]
    imgs = listdir(compareToDir)
    for img in imgs:
        src = cv2.imread(compareToDir + "/" + img)
        res = cv2.imread("demo/result/" + img.replace(".jpg", "_glass.png"))
        res = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)

        mask3 = cv2.merge([res, res, res])

        dimmed = (src * 0.25).astype(np.uint8)
        masked = cv2.bitwise_and(src, src, mask=res)
        out = np.where(mask3 == 0, dimmed, src)

        contours, _ = cv2.findContours(res, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, contours, -1, (0, 255, 0), thickness=1)

        cv2.imshow("bitand", out)
        cv2.waitKey(0)


if __name__ == "__main__":
    main()
