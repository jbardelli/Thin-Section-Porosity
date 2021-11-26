import cv2
import numpy as np
import os
from glob import glob

directory = "./porosity_dataset/ppl"
mask_dir = "./porosity_dataset/masks/"
image_files = sorted(glob(os.path.join(directory, "*")))

for i, image_path in enumerate(image_files):
    path = os.path.splitext(image_path)[0]
    mask_file = mask_dir + path.split("\\")[-1] + '.tiff'
    print(mask_file)
    img = cv2.imread(image_path)
    print(image_path)
    original = img.copy()
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (90, 50, 20), (130, 255, 255))

    kernel = np.ones((3, 3), np.uint8)
    erosion = cv2.erode(mask, kernel, iterations=2)

    # contours, hierarchy = cv2.findContours(erosion, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    # print(contours)
    # cv2.drawContours(resized, contours, -1, (0, 0, 255), 3)

    # cv2.imshow('contours', resized)
    res_img = []
    res_ero = []
    size = (600, 450)
    res_img = cv2.resize(original, size)
    res_ero = cv2.resize(erosion, size)
    cv2.imshow('erosion', res_ero)
    cv2.imshow('orig', res_img)
    mask_f = mask
    mask_f[mask_f == 255] = 1
    cv2.imwrite(mask_file, mask_f)
    # cv2.waitKey(0)


