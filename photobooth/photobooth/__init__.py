import io
import logging
import os
import subprocess
import sys
import time
import datetime

from threading import Thread, Event
from multiprocessing import Process

import numpy as np
import cv2
import gphoto2 as gp

from photobooth.photoserver import app

logging.basicConfig(
    format='%(levelname)s: %(name)s: %(message)s', level=logging.INFO)


class Photobooth:

    def __init__(self, image_dir=".",
                 fullscreen=False,
                 start_server=False,
                 server_only=False,
                 verbose=False,
                 thumb_width=500):
        self.image_dir = image_dir
        self.timer_limit = 3
        self.fullscreen = fullscreen
        self.start_server = start_server
        self.server_only = server_only
        self.server_thread = None
        self.thumb_width = thumb_width

        # setup logger
        self.log = logging.getLogger("Photobooth")
        self.log.setLevel(logging.DEBUG if verbose else logging.INFO)
        format = logging.Formatter('%(levelname)s: %(name)s: %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(format)
        self.log.handlers.append(handler)

        # threading
        self.event = Event()

        # start HTTP server
        if self.start_server:
            self.server_thread = Process(target=self.run_server)
            self.server_thread.start()

    def __del__(self):
        if self.server_thread.is_alive():
            self.log.info("close server...")
            self.server_thread.terminate()
            self.server_thread.join()

    def init_camera(self):
        callback_obj = gp.check_result(gp.use_python_logging())
        camera = gp.check_result(gp.gp_camera_new())
        gp.check_result(gp.gp_camera_init(camera))
        # required configuration will depend on camera type!
        self.log.info('Checking camera config')
        # get configuration tree
        config = gp.check_result(gp.gp_camera_get_config(camera))
        # find the image format config item
        OK, image_format = gp.gp_widget_get_child_by_name(config, 'imageformat')
        if OK >= gp.GP_OK:
            # get current setting
            value = gp.check_result(gp.gp_widget_get_value(image_format))
            # make sure it's not raw
            if 'raw' in value.lower():
                self.log.error('Cannot preview raw images')
                return None
        # find the capture size class config item
        # need to set this on my Canon 350d to get preview to work at all
        OK, capture_size_class = gp.gp_widget_get_child_by_name(config, 'capturesizeclass')
        if OK >= gp.GP_OK:
            # set value
            value = gp.check_result(gp.gp_widget_get_choice(capture_size_class, 2))
            gp.check_result(gp.gp_widget_set_value(capture_size_class, value))
            # set config
            gp.check_result(gp.gp_camera_set_config(camera, config))
        return camera

    def run_server(self):
        self.log.info("starting flask server")
        app.config["IMAGE_DIR"] = self.image_dir
        app.run("0.0.0.0", debug=True)

    def preview(self):
        # loop if server only
        if self.server_only:
            while self.event.wait(1):
                continue
            return 0

        # init camera
        camera = self.init_camera()

        # open window
        if self.fullscreen:
            self.log.debug("Open fullscreen window")
            cv2.namedWindow("preview", cv2.WINDOW_FULLSCREEN)
            cv2.setWindowProperty("preview", 0, 1)
        else:
            self.log.debug("Open window")

        # start preview
        if camera is not None:
            # capture preview image (not saved to camera memory card)
            t0 = time.time()
            timer_active = False
            trigger = False
            i = 0
            while not self.event.is_set():
                self.log.debug('Capturing preview image {:03d}'.format(i))
                camera_file = gp.check_result(gp.gp_camera_capture_preview(camera))
                file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                # decode image
                img = cv2.imdecode(np.fromstring(io.BytesIO(file_data).read(), np.uint8), 1)
                width, height = img.shape[1], img.shape[0]
                # draw timer if active
                if timer_active:
                    time_left = self.timer_limit - (time.time() - t0)
                    if time_left <= 0:
                        time_left = 0
                        trigger = True
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    text = "{:d}".format(int(time_left))
                    textsize = cv2.getTextSize(text, font, 1, 2)[0]
                    # get coords based on boundary
                    textX = int((width / 2 - textsize[0] / 2))
                    textY = int((height / 2 + textsize[1] / 2))
                    cv2.putText(img, text, (textX, textY), font, 20, (255, 255, 255), 10, cv2.LINE_AA)
                # display image
                cv2.imshow("preview", img)
                k = cv2.waitKey(1)
                if k == 27:
                    break
                elif k == 32 or trigger:  # SPACE = direct photo
                    self.take_photo(camera, self.path_images)

                    # reset trigger and timer
                    trigger = timer_active = False
                elif k == 97:  # a - photo after 3 seconds
                    t0 = time.time()
                    timer_active = True

                i += 1
            gp.check_result(gp.gp_camera_exit(camera))
        return 0

    def take_photo(self, camera, path):
        self.log.info("Capturing image")
        file_path = gp.check_result(gp.gp_camera_capture(
            camera, gp.GP_CAPTURE_IMAGE))
        self.log.info("Camera file path: {0}/{1}".format(file_path.folder, file_path.name))
        target = os.path.join(path, self.get_image_name())
        self.log.info("Copying image to {}".format(target))
        camera_file = gp.check_result(gp.gp_camera_file_get(
            camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
        gp.check_result(gp.gp_file_save(camera_file, target))
        self.log.warning("ToDo: make thumbnail?")
        Process(target=self.create_thumb, args=(target,)).start()

    def get_image_name(self):
        return "{}.jpg".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

    @property
    def path_images(self):
        path = os.path.join(self.image_dir, "images")
        if not os.path.exists(path):
            os.mkdir(path)
        return path

    @property
    def path_thumbs(self):
        path = os.path.join(self.image_dir, "thumbs")
        if not os.path.exists(path):
            os.mkdir(path)
        return path

    def create_thumb(self, path):
        self.log.info("creating thumbnail for {}".format(path))
        basename = os.path.basename(path)
        img = cv2.imread(path)

        if img.shape[1] < self.thumb_width:
            cv2.imwrite(img, os.path.join(self.path_thumbs, basename))
            return
        factor = self.thumb_width / float(img.shape[1])
        resized = cv2.resize(img, None, fx=factor, fy=factor)

        thumbnail_path = os.path.join(self.path_thumbs, basename)
        self.log.info("save thumbail to {}".format(thumbnail_path))
        cv2.imwrite(thumbnail_path, resized)

    def create_gif(self, path):
        self.log.info("TODO: create GIF")
