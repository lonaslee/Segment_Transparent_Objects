import os
import numpy as np
import sys
import cv2

from PIL import Image

color_map = {
    0: (0, 0, 0), # background
    1: (255, 0, 0), # water
    2: (0, 255, 0), # wine
    3: (0, 0, 255), # juice
    4: (255, 255, 0), # cocktails
    5: (255, 0, 255), # soda
    6: (255, 255, 255), # coffee
    7: (0, 255, 255), # tea
    8: (50, 0, 0), # boba
    9: (0, 50, 0), # chemical
    10: (0, 0, 50), # medical
    11: (50, 50, 0), # milk
    12: (50, 0, 50), # spirits
    13: (50, 50, 50), # honey
    14: (0, 50, 50), # misc
    15: (100, 200, 255), # misc
}

if __name__ == '__main__':
    path = sys.argv[1]
    assert os.path.exists(path)
    if os.path.isdir(path):
        files = [os.path.join(path, f) for f in os.listdir(path)]
    else:
        files = [path]
    print(f"Viewing {len(files)} mask{'s' if len(files) != 1 else ''}:")
    for file in files:
        print('\t' + file)

    for file in files:
        print(file)
        mask_gray = np.array(Image.open(file).convert("L"))
        print(np.unique(mask_gray))
        mask = np.zeros((*mask_gray.shape, 3), dtype=np.uint8)
        for ival in range(1, 16):
            mask[mask_gray == ival] = color_map[ival]
        
        cv2.imshow('mask', np.hstack((mask, mask)))
        while True:
            k = cv2.waitKey()
            print(k)
            if k == 113 or k == -1: exit(0)
            if k == 114:
                mask = cv2.resize(mask, (800, 600))
                cv2.imshow('mask', np.hstack((mask, mask)))
            else:
                break
    print("Done")
        
