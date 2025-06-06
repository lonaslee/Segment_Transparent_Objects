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

name_map = {
    0: 'background',
    1: 'water',
    2: 'wine',
    3: 'juice',
    4: 'cocktails',
    5: 'soda',
    6: 'coffee',
    7: 'tea',
    8: 'boba',
    9: 'chemical',
    10: 'medical',
    11: 'milk',
    12: 'spirits',
    13: 'honey',
    14: 'misc',
    15: 'misc'
}

if __name__ == '__main__':
    mask_folder = sys.argv[1]
    assert os.path.exists(mask_folder)
    if os.path.isdir(mask_folder):
        mask_files = os.listdir(mask_folder)
    else:
        mask_files = [mask_folder]
    print(f"Viewing {len(mask_files)} mask{'s' if len(mask_files) != 1 else ''}:")
    for mask_file in mask_files:
        print('\t' + mask_file)

    img_folder: str | None = None
    if len(sys.argv) == 3:
        img_folder = sys.argv[2]

    for mask_file in mask_files:
        full_mask_file = os.path.join(mask_folder, mask_file)
        print(full_mask_file)
        mask_gray = np.array(Image.open(full_mask_file).convert("L"))
        classes =np.unique(mask_gray).tolist()
        classes.remove(0)
        print('\tclasses:', classes)
        print('\tnames:  ', [name_map[v] for v in classes])
        mask = np.zeros((*mask_gray.shape, 3), dtype=np.uint8)
        for ival in range(1, 16):
            mask[mask_gray == ival] = color_map[ival]
        
        img = None
        if img_folder:
            img = np.array(Image.open(os.path.join(img_folder, mask_file.replace('.png', '.jpg'))).convert("RGB"))

        cv2.imshow('mask', np.hstack((mask, img if img is not None else mask)))
        while True:
            k = cv2.waitKey()
            if k == 113 or k == -1: exit(0)
            if k == 114:
                mask = cv2.resize(mask, (800, 600))
                img = cv2.resize(img, (800, 600))
                cv2.imshow('mask', np.hstack((mask, img if img is not None else mask)))
            else:
                break
        print()
    print("Done")
        
