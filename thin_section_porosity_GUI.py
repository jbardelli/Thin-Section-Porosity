import numpy as np
from cv2 import cv2
from PIL import Image, ImageTk
from petrographic_image_utils import mosaic, draw_pores, draw_lines, draw_scale, save_annotated_img, calc_pore_params, \
    calc_histogram, calc_porosity, results_to_csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox
from GUI_Utils import *


class App:
    def __init__(self, window, window_title):
        self.ppl_image = np.zeros(shape=[3200, 2400, 3], dtype=np.uint8)
        self.ann_image = np.zeros(shape=[3200, 2400, 3], dtype=np.uint8)
        self.pore_dist_bins = [0, 4, 20, 64, 125, 500, 1000, 100000]  # Bins declares in micrometers
        self.files = []
        self.window = window
        self.window.title(window_title)
        self.delta = 0.75
        self.imscale = 1.0
        self.imageid = None
        self.fit_window_flag = 0

        # Tkinter window definitions
        # Image Canvas
        self.canvas_frame = frame_create(window, text_="Image", row_=0, col_=0, colspan_=1, rowspan_=5)
        self.canvas = tk.Canvas(self.canvas_frame, width=920, height=690)
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        xscrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        xscrollbar.grid(row=1, column=0, sticky=tk.E+tk.W)
        yscrollbar = tk.Scrollbar(self.canvas_frame)
        yscrollbar.grid(row=0, column=1, sticky=tk.N+tk.S)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
        self.canvas.grid(row=0, column=0, rowspan=4)
        xscrollbar.config(command=self.canvas.xview)
        yscrollbar.config(command=self.canvas.yview)

        # Enable using the mouse:
        # self.canvas.bind("<ButtonPress-1>", self.move_from)
        # self.canvas.bind("<B1-Motion>", self.move_to)
        self.canvas.bind('<MouseWheel>', self.wheel)

        # HSV Frame
        self.hsv_frame = frame_create(window, text_="HSV Space", row_=0, col_=1, colspan_=2, rowspan_=1)
        self.h_max = tk.IntVar(value=130)
        self.h_max.trace("w", self.threshold_image)
        self.hmax = tk.Scale(self.hsv_frame, variable=self.h_max, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Hmax', length=189)
        self.hmax.grid(row=1, column=0, columnspan=2, padx=14, pady=0)
        self.h_min = tk.IntVar(value=90)
        self.h_min.trace("w", self.threshold_image)
        self.hmin = tk.Scale(self.hsv_frame, variable=self.h_min, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Hmin', length=189)
        self.hmin.grid(row=2, column=0, columnspan=2, padx=14, pady=0)
        self.s_max = tk.IntVar(value=255)
        self.s_max.trace("w", self.threshold_image)
        self.smax = tk.Scale(self.hsv_frame, variable=self.s_max, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Smax', length=189)
        self.smax.grid(row=3, column=0, columnspan=2, padx=14, pady=0)
        self.s_min = tk.IntVar(value=50)
        self.s_min.trace("w", self.threshold_image)
        self.smin = tk.Scale(self.hsv_frame, variable=self.s_min, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Smin', length=189)
        self.smin.grid(row=4, column=0, columnspan=2, padx=14, pady=0)
        self.v_max = tk.IntVar(value=255)
        self.v_max.trace("w", self.threshold_image)
        self.vmax = tk.Scale(self.hsv_frame, variable=self.v_max, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Vmax', length=189)
        self.vmax.grid(row=5, column=0, columnspan=2, padx=14, pady=0)
        self.v_min = tk.IntVar(value=20)
        self.v_min.trace("w", self.threshold_image)
        self.vmin = tk.Scale(self.hsv_frame, variable=self.v_min, orient=tk.HORIZONTAL, from_=0, to=255, resolution=5,
                             label='Vmin', length=189)
        self.vmin.grid(row=6, column=0, columnspan=2, padx=14, pady=0)

        self.scale_frame = frame_create(window, text_="Pixel Scale", row_=1, col_=1, colspan_=2, rowspan_=1)
        self.px_scale = tk.DoubleVar(value=1.0)
        entry_create(self.scale_frame, width_=15, row_=0, col_=1, pad_x=5, pad_y=8, label="um x pixel",
                     var=self.px_scale)
        self.scale_label = tk.DoubleVar(value=100)
        entry_create(self.scale_frame, width_=15, row_=1, col_=1, pad_x=5, pad_y=8, label="Label", var=self.scale_label)

        self.open_button = tk.Button(self.window, text='Open Files', command=self.select_files)
        self.open_button.grid(row=2, column=1, columnspan=1, padx=55, pady=3)
        self.save_button = tk.Button(self.window, text='Calculate and Save', command=self.calc_and_save)
        self.save_button.grid(row=3, column=1, columnspan=1, padx=55, pady=3)

        self.delay = 500
        self.show_image()
        self.window.mainloop()

    def move_from(self, event):
        self.canvas.scan_mark(event.x, event.y)
        print('from')

    def move_to(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        print('to')

    def wheel(self, event):
        # Zoom with mouse wheel
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:
            scale *= self.delta
            self.imscale *= self.delta
        if event.num == 4 or event.delta == 120:
            scale /= self.delta
            self.imscale /= self.delta
        # Rescale all canvas objects
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.canvas.scale(tk.ALL, x, y, scale, scale)
        self.show_image()
        self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL))

    def show_image(self):
        ''' Show image on the Canvas '''
        if len(self.files) == 4:
            if self.imageid:
                self.canvas.delete(self.imageid)
                self.imageid = None
                self.canvas.imagetk = None  # delete previous image from the canvas
                print('Delete previous image...')
            width, height, channels = self.ann_image.shape
            new_size = int(self.imscale * width), int(self.imscale * height)
            # Use self.text object to set proper coordinates
            print('new_size=',new_size)
            print(self.fit_window_flag)
            if self.fit_window_flag == 0:
                self.ann_image = cv2.resize(self.ann_image, new_size)
                imagetk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(self.ann_image, cv2.COLOR_BGR2RGB)), size=new_size)
                self.imageid = self.canvas.create_image(0, 0, image=imagetk)
                print('flag=0')
            else:
                self.fit_window_flag = 0
                self.ann_image = cv2.resize(self.ann_image, (920, 690))
                imagetk = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(self.ann_image, cv2.COLOR_BGR2RGB)))
                self.imageid = self.canvas.create_image(0, 0, image=imagetk, anchor=tk.NW)
                print('flag=1')
            self.canvas.lower(self.imageid)             # set it into background
            self.canvas.imagetk = imagetk               # keep an extra reference to prevent garbage-collection
        # self.window.after(self.delay, self.show_image)  # Repeat after self.delay

    # def update(self):  # This Function executes every self.delay
    #     if len(self.files) == 4:
    #         # show_image = cv2.resize(self.ann_image, (920, 690))
    #         show_image = self.ann_image
    #         show_image = cv2.cvtColor(show_image, cv2.COLOR_BGR2RGB)
    #         self.photo = ImageTk.PhotoImage(image=Image.fromarray(show_image))  # Create photo from array
    #         self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)      # Set image to center of canvas
    #     self.window.after(self.delay, self.update)  # Repeat after self.delay

    def select_files(self):
        filetypes = (('image files', '.jpg .tiff .jpeg .png'), ('All files', '*.*'))
        image = [0, 0, 0, 0]
        filenames = fd.askopenfilenames(title='Open files', initialdir='/Documents', filetypes=filetypes)
        if len(filenames) != 4:
            messagebox.showerror("Error", "Only 4 files can be selected")
        else:
            self.files = filenames
            for i in range(len(filenames)):
                image[i] = cv2.imread(filenames[i])
            self.ppl_image = mosaic(image[0], image[1], image[2], image[3])  # Make a mosaic with all 4 images
            draw_lines(self.ppl_image)
            self.ann_image = self.ppl_image.copy()
            self.fit_window_flag = 1
            self.threshold_image()


    def threshold_image(self, *args):
        hsv = cv2.cvtColor(self.ppl_image, cv2.COLOR_BGR2HSV)  # Convert to to HSV color scheme
        bin_image = cv2.inRange(hsv, (self.h_min.get(), self.s_min.get(), self.v_min.get()),
                                (self.h_max.get(), self.s_max.get(), self.v_max.get()))  # Threshold image
        kernel = np.ones((3, 3), np.uint8)
        erosion = cv2.erode(bin_image, kernel, iterations=2)  # Erode to reduce noise
        bin_image = cv2.merge([erosion, erosion, erosion])  # Merge 2D binary array to 3 channel image
        pore_df, diam, contours = calc_pore_params(bin_image, scale=self.px_scale.get())  # Calculate pore parameters
        self.ann_image = self.ppl_image.copy()
        cv2.drawContours(self.ann_image, contours, -1, color=(0, 0, 255), thickness=3, lineType=cv2.LINE_8)
        draw_scale(self.ann_image, self.px_scale.get(), self.scale_label.get())
        self.show_image()

    def calc_and_save(self):
        hsv = cv2.cvtColor(self.ppl_image, cv2.COLOR_BGR2HSV)  # Convert to to HSV color scheme
        bin_image = cv2.inRange(hsv, (self.h_min.get(), self.s_min.get(), self.v_min.get()),
                                (self.h_max.get(), self.s_max.get(), self.v_max.get()))  # Threshold image
        # kernel = np.ones((3, 3), np.uint8)
        # erosion = cv2.erode(bin_image, kernel, iterations=0)  # Erode to reduce noise
        bin_image = cv2.merge([bin_image, bin_image, bin_image])  # Merge 2D binary array to 3 channel image
        # --- CALCULATIONS ---
        pore_df, diam, contours = calc_pore_params(bin_image, scale=self.px_scale.get())  # Calculate pore parameters
        hist_df = calc_histogram(diam, self.pore_dist_bins)  # Calculate histogram with provided bins
        porosity, poro_df = calc_porosity(bin_image)  # Calculate total porosity

        # --- SAVE RESULTS ---
        results_folder = "./prediction_results/"  # Target folder to save results
        results_to_csv(poro_df, hist_df, pore_df, results_folder, self.files[0])  # Save dataframes to csv
        self.ann_image = self.ppl_image.copy()
        draw_pores(contours, self.ann_image, self.pore_dist_bins,
                   scale=self.px_scale.get())  # Draw pore filled with colors
        draw_scale(self.ann_image, self.px_scale.get(), self.scale_label.get())
        save_annotated_img(self.ann_image, results_folder, self.files[0])  # Save annotated image to file
        self.fit_window_flag = 1
        self.show_image()


if __name__ == "__main__":
    App(tk.Tk(), "Thin Section Porosity")
