import numpy as np
import pandas as pd
import math
import os
from cv2 import cv2
from tqdm import tqdm


def calc_pore_params(bin_img, col_img, bins, scale=1):      # Scale is um per pixel
    gray = cv2.cvtColor(bin_img, cv2.COLOR_BGR2GRAY)        # Convert into grayscale
    contours, hierarchy = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    total_pix = bin_img.shape[0] * bin_img.shape[1]         # Total pixels in the mosaic image to calculate porosity

    pore_areas, bin_areas = calc_pore_area(contours, hierarchy, bins, scale, bin_img, col_img)

    porosity = np.round(np.sum(pore_areas)/total_pix*100, 1)    # Calculate total porosity with pore_areas
    print('Total porosity (binary image): ', np.round(np.count_nonzero(gray) / total_pix * 100, 1))
    print('Total porosity (pore_areas): ', porosity)
    porof = pd.DataFrame(data=[porosity])                       # Create pandas df for save_to_csv
    porof.columns = ['POROSITY[%]']                             # Add column header to pandas df

    bin_percent = np.round(bin_areas / total_pix * 100, 2)      # Calculate bin area as percentage of total pixels
    print('Histogram (%): ', bin_percent)                       # Print Histogram
    dataf = pd.DataFrame(data=bin_percent)                      # Create pandas df for save_to_csv
    dataf = dataf.T                                             # Transpose table
    dataf.columns = ['MICROPORO', 'MESOPORO', 'MACROPORO FINO', 'MACROPORO GRUESO', 'MEGAPORO']  # Add column headers to pandas df
    return porof, dataf


def calc_pore_area(cont, hier, bins, scale, bin_img, col_img):
    colours = [(0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0), (255, 0, 255)]  # Colors for different sizes

    pore_areas = np.zeros(len(cont))                        # Initialize arrays
    diameters = np.zeros(len(cont))                         # Initialize arrays
    bin_areas = np.zeros(len(bins) - 1)                     # Array stores the sum of areas for each bin
    for i in tqdm(range(len(cont))):
        if cv2.contourArea(cont[i]) > 0:
            if hier[0][i][3] < 0:
                blank_img = np.zeros((bin_img.shape[0], bin_img.shape[1]))
                cv2.drawContours(blank_img, cont, i, color=(255, 255, 255), thickness=-1, hierarchy=hier, maxLevel=2)
                area = np.count_nonzero(blank_img)                  # Calculate pore area
                diameter = math.sqrt(4 * area / math.pi) * scale    # Equivalent circle diameter of same area
                # print('Area(px): ', area, ' / Diameter(um)', diameter)
                for j in range(len(bins) - 1):                      # Cycle through all diameter histogram bins
                    if bins[j] < diameter <= bins[j + 1]:           # If diameter is between bin thresholds, then...
                        pore_areas[i] = area                        # Assign pore area
                        diameters[i] = diameter                     # Assign diameter
                        bin_areas[j] += area                        # Increment the area of the bin with current pore area
                        cv2.drawContours(col_img, cont, i, color=colours[j], thickness=-1, hierarchy=hier, maxLevel=2)  # Draw pore into color image
    return pore_areas, bin_areas


def results_to_csv(poro_df, hist_df, results_folder, image_path):
    tail = os.path.split(image_path)[-1]
    csv_path = results_folder + tail.split(".")[0] + ".csv"
    poro_df.to_csv(csv_path)
    hist_df.to_csv(csv_path, mode='a')
    return


def save_annotated_img(image, results_folder, image_path):
    tail = os.path.split(image_path)[-1]
    result_img_path = results_folder + tail.split(".")[0] + "_result.tiff"
    cv2.imwrite(result_img_path, image)
    return


def mosaic(image1, image2, image3, image4):
    concat1 = cv2.hconcat([image1, image2])
    concat2 = cv2.hconcat([image3, image4])
    final = cv2.vconcat([concat1, concat2])
    return final


def draw_scale(image, scale, label):                # Draw a scale on top of the image in RED color
    resol_x = int(image.shape[1]/2)
    resol_y = int(image.shape[0]/2)
    line_length = int(label / scale)
    for i in range(2):                              # Draw in the four images
        for j in range(2):
            pos_x = int(resol_x * 11 / 12) + i * resol_x
            pos_y = int(resol_y * 11 / 12) + j * resol_y
            cv2.line(image, (pos_x, pos_y), (pos_x-line_length, pos_y), color=(0, 0, 255), thickness=5)
            cv2.putText(image, str(label)+'um', (pos_x-line_length, pos_y-10), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, color=(0, 0, 255), thickness=3, lineType=cv2.LINE_AA)


def draw_lines(image):                              # Draw center lines that divide the four images
    center_y = int(image.shape[0]/2)                # to avoid pores that are different to be interpreted as the same
    center_x = int(image.shape[1]/2)                # between images of different sectors of the thin section
    cv2.line(image, (0, center_y), (image.shape[1], center_y), color=(0, 0, 0), thickness=2)
    cv2.line(image, (center_x, 0), (center_x, image.shape[0]), color=(0, 0, 0), thickness=2)
