# -*- coding: utf-8 -*-
# Advanced zoom example. Like in Google Maps.
# It zooms only a tile, but not the whole image. So the zoomed tile occupies
# constant memory and not crams it with a huge resized image for the large zooms.
import numpy as np
from cv2 import cv2
from petrographic_image_utils import mosaic, draw_lines, draw_scale, save_annotated_img, calc_pore_params, results_to_csv
from GUI_Utils import *
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox
from PIL import Image, ImageTk


class AutoScrollbar(ttk.Scrollbar):
    """ A scrollbar that hides itself if it's not needed.
        Works only if you use the grid geometry manager """
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with this widget')

    def place(self, **kw):
        raise tk.TclError('Cannot use place with this widget')


class ZoomAdvanced(ttk.Frame):
    """ Advanced zoom of the image """
    def __init__(self, mainframe):
        """ Initialize the main Frame """
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title('Thin Section Porosity')
        # Program variables
        self.ppl_image = np.zeros(shape=[800, 600, 3], dtype=np.uint8)
        self.ann_image = np.zeros(shape=[800, 600, 3], dtype=np.uint8)
        self.pore_dist_bins = [0, 64, 125, 500, 1000, 100000]  # Bins declares in micrometers
        self.files = []

        # HSV Frame
        self.hsv_frame = frame_create(self.master, text_="HSV Space", row_=0, col_=1, colspan_=2, rowspan_=1)
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
        # Scale Frame sets the scale in pixels/um and the size of the scale to be drawn on the images
        self.scale_frame = frame_create(self.master, text_="Pixel Scale", row_=1, col_=1, colspan_=2, rowspan_=1)
        self.px_scale = tk.DoubleVar(value=1.0)
        self.px_scale.trace("w", self.threshold_image)
        entry_create(self.scale_frame, width_=15, row_=0, col_=1, pad_x=5, pad_y=8, label="um x pixel",
                     var=self.px_scale)
        self.scale_label = tk.IntVar(value=100)
        self.scale_label.trace("w", self.threshold_image)
        entry_create(self.scale_frame, width_=15, row_=1, col_=1, pad_x=5, pad_y=8, label="Label", var=self.scale_label)
        # Buttons Frame
        self.button_frame = frame_create(self.master, text_="Commands", row_=2, col_=1, colspan_=2, rowspan_=1)
        self.open_button = tk.Button(self.button_frame, text='Open Files', command=self.select_files)
        self.open_button.grid(row=2, column=1, columnspan=1, padx=55, pady=3)
        self.save_button = tk.Button(self.button_frame, text='Calculate and Save', command=self.calc_and_save)
        self.save_button.grid(row=3, column=1, columnspan=1, padx=55, pady=3)

        # Vertical and horizontal scrollbars for canvas
        self.img_frame = frame_create(self.master, text_="Image", row_=0, col_=0, colspan_=1, rowspan_=6)
        vbar = AutoScrollbar(self.img_frame, orient='vertical')
        hbar = AutoScrollbar(self.img_frame, orient='horizontal')
        vbar.grid(row=0, column=1, sticky='ns')
        hbar.grid(row=1, column=0, sticky='we')
        # Create canvas and put image on it
        self.canvas = tk.Canvas(self.img_frame, highlightthickness=0, xscrollcommand=hbar.set, yscrollcommand=vbar.set, width=800, height=600)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        vbar.configure(command=self.scroll_y)  # bind scrollbars to the canvas
        hbar.configure(command=self.scroll_x)
        # Make the canvas expandable
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        # Bind events to the Canvas
        # self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>',     self.move_to)
        self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
        self.imscale = 1.0      # scale for the canvas image
        self.delta = 1.3        # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.image = Image.fromarray(cv2.cvtColor(self.ann_image, cv2.COLOR_BGR2RGB))
        self.width, self.height = self.image.size
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)

    def scroll_y(self, *args, **kwargs):
        """ Scroll canvas vertically and redraw the image """
        self.canvas.yview(*args)  # scroll vertically
        self.show_image()                   # redraw the image

    def scroll_x(self, *args, **kwargs):
        """ Scroll canvas horizontally and redraw the image """
        self.canvas.xview(*args)  # scroll horizontally
        self.show_image()                   # redraw the image

    def move_from(self, event):
        """ Remember previous coordinates for scrolling with the mouse """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """ Drag (move) canvas to the new position """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()                   # redraw the image

    def wheel(self, event):
        """ Zoom with mouse wheel """
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)     # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
            pass                                    # Ok! Inside the image
        else:
            return                                  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down
            i = min(self.width, self.height)
            if int(i * self.imscale) < 30:
                return  # image is less than 30 pixels
            self.imscale /= self.delta
            scale /= self.delta
        if event.num == 4 or event.delta == 120:  # scroll up
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if i < self.imscale:
                return  # 1 pixel is bigger than the visible area
            self.imscale *= self.delta
            scale *= self.delta
        self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects
        self.show_image()

    def show_image(self, event=None):
        """ Show image on the Canvas """
        bbox1 = self.canvas.bbox(self.container)  # get image area
        # Remove 1 pixel shift at the sides of the bbox1
        bbox1 = (bbox1[0] + 1, bbox1[1] + 1, bbox1[2] - 1, bbox1[3] - 1)
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]),  # get scroll region box
                max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3])]
        if bbox[0] == bbox2[0] and bbox[2] == bbox2[2]:  # whole image in the visible area
            bbox[0] = bbox1[0]
            bbox[2] = bbox1[2]
        if bbox[1] == bbox2[1] and bbox[3] == bbox2[3]:  # whole image in the visible area
            bbox[1] = bbox1[1]
            bbox[3] = bbox1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x1 = max(bbox2[0] - bbox1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(bbox2[1] - bbox1[1], 0)
        x2 = min(bbox2[2], bbox1[2]) - bbox1[0]
        y2 = min(bbox2[3], bbox1[3]) - bbox1[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            x = min(int(x2 / self.imscale), self.width)   # sometimes it is larger on 1 pixel...
            y = min(int(y2 / self.imscale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x1 / self.imscale), int(y1 / self.imscale), x, y))
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1))))
            imageid = self.canvas.create_image(max(bbox2[0], bbox1[0]), max(bbox2[1], bbox1[1]), anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

    def select_files(self):
        filetypes = (('image files', '.jpg .tiff .jpeg .tif'), ('All files', '*.*'))
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
            self.height, self.width, _ = self.ann_image.shape
            self.imscale = 1
            self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
            self.threshold_image()

    def threshold_image(self, *args):
        hsv = cv2.cvtColor(self.ppl_image, cv2.COLOR_BGR2HSV)           # Convert to to HSV color scheme
        bin_image = cv2.inRange(hsv, (self.h_min.get(), self.s_min.get(), self.v_min.get()),
                                (self.h_max.get(), self.s_max.get(), self.v_max.get()))  # Threshold image
        bin_image = cv2.merge([bin_image, bin_image, bin_image])        # Merge 2D binary array to 3 channel image
        gray = cv2.cvtColor(bin_image, cv2.COLOR_BGR2GRAY)              # Convert into grayscale
        contours, hierarchy = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        self.ann_image = self.ppl_image.copy()
        cv2.drawContours(self.ann_image, contours, -1, color=(0, 0, 255), thickness=1, lineType=cv2.LINE_AA)
        draw_scale(self.ann_image, self.px_scale.get(), self.scale_label.get())
        self.image = Image.fromarray(cv2.cvtColor(self.ann_image, cv2.COLOR_BGR2RGB))
        self.show_image()

    def calc_and_save(self):
        hsv = cv2.cvtColor(self.ppl_image, cv2.COLOR_BGR2HSV)           # Convert to to HSV color scheme
        bin_image = cv2.inRange(hsv, (self.h_min.get(), self.s_min.get(), self.v_min.get()),
                                (self.h_max.get(), self.s_max.get(), self.v_max.get()))  # Threshold image
        bin_image = cv2.merge([bin_image, bin_image, bin_image])              # Merge 2D binary array to 3 channel image

        # --- CALCULATIONS ---
        self.ann_image = self.ppl_image.copy()
        phi_df, hist_df = calc_pore_params(bin_image, self.ann_image, self.pore_dist_bins, scale=self.px_scale.get())     # Calculate pore parameters

        # --- SAVE RESULTS ---
        results_folder = "./prediction_results/"                                        # Target folder to save results
        results_to_csv(phi_df, hist_df, results_folder, self.files[0])                  # Save dataframes to csv
        draw_scale(self.ann_image, self.px_scale.get(), self.scale_label.get())         # Draw the scale in microns in the four images
        save_annotated_img(self.ann_image, results_folder, self.files[0])               # Save annotated image to file
        self.image = Image.fromarray(cv2.cvtColor(self.ann_image, cv2.COLOR_BGR2RGB))   # Convert image to RGB and to PIL format to show on canvas
        self.show_image()


root = tk.Tk()
root.geometry("+0+0")
app = ZoomAdvanced(root)
root.mainloop()
