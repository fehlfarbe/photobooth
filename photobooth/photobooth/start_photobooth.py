import io
import logging
import os
import subprocess
import sys
import time
import datetime

from threading import Thread, Event

import numpy as np
import cv2
import gphoto2 as gp

class Photobooth:

    def __init__(self, target_dir="/home/kolbe/"):
        self.target_dir = target_dir
        self.timer_limit = 3

        # setup logger
        logging.basicConfig(
            format='%(levelname)s: %(name)s: %(message)s', level=logging.INFO)

        self.event = Event()

    def init_camera(self):
        callback_obj = gp.check_result(gp.use_python_logging())
        camera = gp.check_result(gp.gp_camera_new())
        gp.check_result(gp.gp_camera_init(camera))
        # required configuration will depend on camera type!
        logging.info('Checking camera config')
        # get configuration tree
        config = gp.check_result(gp.gp_camera_get_config(camera))
        # find the image format config item
        OK, image_format = gp.gp_widget_get_child_by_name(config, 'imageformat')
        if OK >= gp.GP_OK:
            # get current setting
            value = gp.check_result(gp.gp_widget_get_value(image_format))
            # make sure it's not raw
            if 'raw' in value.lower():
                logging.error('Cannot preview raw images')
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

    def preview(self):
        camera = self.init_camera()
        if camera is not None:
            # capture preview image (not saved to camera memory card)
            t0 = time.time()
            timer_active = False
            trigger = False
            i = 0
            while not self.event.is_set():
                logging.debug('Capturing preview image {:03d}'.format(i))
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
                if k == 32 or trigger:  # SPACE = direct photo
                    logging.info("Capturing image")
                    file_path = gp.check_result(gp.gp_camera_capture(
                        camera, gp.GP_CAPTURE_IMAGE))
                    logging.info("Camera file path: {0}/{1}".format(file_path.folder, file_path.name))
                    target = os.path.join(self.target_dir, file_path.name)
                    logging.info("Copying image to {}".format(target))
                    camera_file = gp.check_result(gp.gp_camera_file_get(
                        camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL))
                    gp.check_result(gp.gp_file_save(camera_file, target))
                    logging.warning("ToDo: make thumbnail?")

                    # reset trigger and timer
                    trigger = timer_active = False
                if k == 97:  # a - photo after 3 seconds
                    t0 = time.time()
                    timer_active = True

                i += 1
            gp.check_result(gp.gp_camera_exit(camera))
        return 0


if __name__ == "__main__":
    photobooth = Photobooth()
    ret = 0
    photobooth.preview()
