from PIL import Image
import numpy as np
import pandas as pd
import math
from cv2 import cv2
import os
from petrographic_image_utils import mosaic


img = cv2.imread("./comp1.jpg")
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)           # Convert to to HSV color scheme
bin_image = cv2.inRange(hsv, (90, 40, 20), (130, 255, 255))  # Threshold image
contours, h = cv2.findContours(bin_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
blank_img1 = np.ones((bin_image.shape[0], bin_image.shape[1]))
print(h)

for i, contour in enumerate(contours):
    if h[0][i][3] < 0:
        cv2.drawContours(blank_img1, contours, i, color=(0, 255, 0), thickness=-1, hierarchy=h, maxLevel=2)

        # blank_img1 = np.ones((bin_image.shape[0], bin_image.shape[1], 3))

cv2.imshow('win1', blank_img1)
cv2.waitKey(0)
