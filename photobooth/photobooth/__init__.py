import io
import logging
import os
import time
import datetime
from imutils.video import VideoStream
from imutils import resize
from enum import Enum
from threading import Thread, Event
from multiprocessing import Process
import numpy as np
import cv2
import gphoto2 as gp
import pygame


logging.basicConfig(
    format='%(levelname)s: %(name)s: %(message)s', level=logging.DEBUG)


class Camera(Enum):
    raspicam = "raspicam"
    v4l2 = "v4l2"
    gphoto2 = "gphoto2"

    def __str__(self):
        return self.value


class Action(Enum):
    none = None
    exit = "exit"
    photo = "photo"
    interval = "interval"
    gif = "gif"
    print_last_photo = "print_last_photo"


class Input:

    def __init__(self):
        # setup logger
        self.log = logging.getLogger(self.__class__.__name__)
        # self.last_action = Action.none
        # self.event = Event()
    #     self.thread = Thread(target=self._update_thread)
    #     self.thread.start()
    #
    # def _update_thread(self):
    #     while not self.event.is_set():
    #         self._update()
    #
    # def _update(self):
    #     raise NotImplementedError

    def close(self):
        pass

    def get_action(self):
        raise NotImplementedError
        # action = self.last_action
        # self.last_action = Action.none
        # return action


class KeyboardInput(Input):

    def __init__(self, keymap=None):
        super(KeyboardInput, self).__init__()
        if keymap is None:
            self.keymap = {pygame.K_a: Action.interval,
                           pygame.K_SPACE: Action.photo,
                           pygame.K_ESCAPE: Action.exit,
                           pygame.K_g: Action.gif,
                           pygame.K_p: Action.print_last_photo}
        else:
            self.keymap = keymap

    def get_action(self):
        try:
            events = pygame.event.get()
            # loop events
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self.log.debug(event.key)
                    self.log.debug(event)
                    self.log.debug(self.keymap)
                    if event.key in self.keymap.keys():
                        return self.keymap[event.key]
        except pygame.error as e:
            self.log.error(e)

        return Action.none


class GPIOInput(Input):

    def __init__(self, pinmap=None, mode=0):
        super(GPIOInput, self).__init__()
        import RPi.GPIO as GPIO
        mode = GPIO.BCM
        GPIO.setmode(mode)
        if pinmap is None:

            self.pinmap = {21: Action.photo,
                           20: Action.interval,
                           26: Action.gif,
                           16: Action.print_last_photo}
        else:
            self.pinmap = pinmap

        self.last_action = Action.none
        self.setup()

    def setup(self):
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        for k in self.pinmap.keys():
            GPIO.setup(k, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(k, GPIO.FALLING, bouncetime=100, callback=self.callback)

    def callback(self, channel):
        if channel in self.pinmap.keys():
            self.last_action = self.pinmap[channel]

    def get_action(self):
        # import RPi.GPIO as GPIO
        # for k in self.pinmap.keys():
        #     if GPIO.event_detected(k):
        #         self.log.debug("Pressed GPIO: {} for {}".format(k, self.pinmap[k]))
        #         return self.pinmap[k]
        action = self.last_action
        self.last_action = Action.none
        return action

    def close(self):
        import RPi.GPIO as GPIO
        GPIO.cleanup()


class Photobooth:

    def __init__(self, image_dir=".",
                 fullscreen=False,
                 verbose=False,
                 thumb_width=500,
                 review_time=2,
                 input_handler=None,
                 server=True):
        self.image_dir = image_dir
        self.timer_limit = 3
        self.fullscreen = fullscreen
        self.thumb_width = thumb_width
        self.review_time = review_time
        if input_handler is None:
            input_handler = [KeyboardInput()]
            try:
                input_handler.append(GPIOInput())
            except Exception as e:
                print(e)
                pass
        self.input_handler = input_handler
        self.start_server = server

        # setup logger
        self.log = logging.getLogger("Photobooth")
        self.log.setLevel(logging.DEBUG if verbose else logging.INFO)

        # pygame window
        self.screen = None

        # threading
        self.event = Event()
        self.server_thread = None
        self.preview_thread = None

        # start HTTP server
        if self.start_server:
            self.server_thread = Thread(target=self.run_server, daemon=True)
            self.server_thread.start()

    def __del__(self):
        self.close()

    def run_server(self):
        self.log.info("start server")
        from gevent.pywsgi import WSGIServer
        from photobooth.photoserver import app
        app.config["IMAGE_DIR"] = self.image_dir
        http_server = WSGIServer(('127.0.0.1', 5000), app)
        http_server.serve_forever()

    def close(self):
        self.event.set()
        if self.preview_thread is not None:
            # self.preview_thread.terminate()
            self.preview_thread.join()
        for handler in self.input_handler:
            handler.close()

    def update_window(self, frame):
        if frame.shape[1] > self.preview_width:
            frame = resize(frame, width=self.preview_width)
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        frame = pygame.transform.flip(frame, True, False)
        self.screen.blit(frame, (0, 0))
        pygame.display.update()

    def show_snap(self, img, review_time=2):
        img_resized = resize(img, width=self.preview_width)

        # show flash
        white = np.ones(img_resized.shape, dtype=np.uint8) * 255
        self.update_window(white)
        time.sleep(0.2)

        # show snapshot
        self.update_window(img_resized)
        time.sleep(review_time)

        # blur image
        for i in np.arange(1, 51, 4):
            frame = cv2.blur(img_resized, (i, i))
            self.update_window(frame)
            time.sleep(0.05)

    def _preview(self):
        # init camera
        camera = self.init_camera()

        # setup window
        flags = 0
        if self.fullscreen:
            flags = pygame.FULLSCREEN
            flags |= pygame.HWSURFACE
        flags |= pygame.DOUBLEBUF
        flags |= pygame.SRCALPHA
        pygame.init()
        pygame.display.set_caption("Photobooth")
        self.screen = pygame.display.set_mode((0, 0), flags, 32)

        # start preview
        if camera is not None:
            # capture preview image (not saved to camera memory card)
            t0 = time.time()
            timer_active = False
            trigger = False
            last_snap = None
            i = 0
            self.event.clear()
            while not self.event.is_set():
                # show last snap
                if last_snap is not None:
                    self.show_snap(last_snap, review_time=self.review_time)
                    last_snap = None
                # self.log.debug('Capturing preview image {:06d}'.format(i))
                img = self.take_preview_image(camera)
                if img is None:
                    self.log.error("Got None image for preview...exit")
                    self.event.set()
                    break
                width, height = img.shape[1], img.shape[0]
                # draw timer if active
                if timer_active:
                    time_left = self.timer_limit - (time.time() - t0)
                    if time_left <= 0:
                        time_left = 0
                        trigger = True
                    font = cv2.FONT_HERSHEY_PLAIN
                    font_scale = 30
                    thickness = 20
                    text = "{:d}".format(int(time_left))
                    # textsize = cv2.getTextSize(text, font, 1, 2)[0]
                    line_width, line_height = cv2.getTextSize(text, font, font_scale, thickness)[0]
                    # get coords based on boundary
                    x = (width - line_width) // 2
                    y = (height + line_height) // 2
                    cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
                # display image
                # cv2.imshow(self.window_title, img)
                self.update_window(img)
                # k = cv2.waitKey(1)
                action = self.get_action()
                if action is not Action.none:
                    self.log.info("ACTION: {}".format(action))
                if action == Action.exit:
                    break
                elif action == Action.photo or trigger:  # SPACE = direct photo
                    # take photo
                    target = self.take_photo(camera, self.path_images)
                    # create thumbnail in new process
                    Thread(target=self.create_thumb, args=(target,)).start()
                    # reset trigger and timer
                    trigger = timer_active = False
                    # load last snap
                    last_snap = cv2.imread(target)
                elif action == Action.interval:  # a - photo after 3 seconds
                    t0 = time.time()
                    timer_active = True
                elif action == Action.gif:
                    self.log.warning("ToDo: GIF is not implemented")
                elif action == Action.print_last_photo:
                    self.log.warning("ToDo: printing last photo is not implemented")
                i += 1
            # cleanup
            self.log.info("cleanup")
            self.close_camera(camera)
            pygame.quit()
        return 0

    @property
    def preview_width(self):
        w, h = self.screen.get_size()
        return w

    def get_action(self):
        for handler in self.input_handler:
            action = handler.get_action()
            if action is not Action.none:
                return action
        return Action.none

    def preview(self, block=True):
        if block:
            return self._preview()
        else:
            self.preview_thread = Thread(target=self._preview)
            self.preview_thread.start()

    def init_camera(self):
        self.log.debug("init camera")
        vs = VideoStream(resolution=(1920, 1080))
        vs.start()
        time.sleep(2.0)
        return vs

    def close_camera(self, camera):
        self.log.debug("close camera")
        camera.stop()

    def take_preview_image(self, camera):
        img = camera.read()
        return resize(img, width=self.preview_width)

    def take_photo(self, camera, path):
        img = camera.read()
        target = os.path.join(path, self.get_image_name())
        cv2.imwrite(target, img)
        return target

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

        # if img.shape[1] < self.thumb_width:
        #     cv2.imwrite(img, os.path.join(self.path_thumbs, basename))
        #     return
        # factor = self.thumb_width / float(img.shape[1])
        # resized = cv2.resize(img, None, fx=factor, fy=factor)
        resized = resize(img, width=self.thumb_width)
        thumbnail_path = os.path.join(self.path_thumbs, basename)
        self.log.info("save thumbail to {}".format(thumbnail_path))
        cv2.imwrite(thumbnail_path, resized)

    def create_gif(self, path):
        self.log.info("TODO: create GIF")


class Raspibooth(Photobooth):

    def init_camera(self):
        self.log.debug("init camera")
        vs = VideoStream(usePiCamera=True, resolution=(1920, 1088))
        vs.start()
        time.sleep(2.0)
        return vs

    def close_camera(self, camera):
        self.log.debug("close camera")
        camera.stop()

    def take_preview_image(self, camera):
        img = camera.read()
        return resize(img, width=self.preview_width)

    def take_photo(self, camera, path):
        img = camera.read()
        target = os.path.join(path, self.get_image_name())
        cv2.imwrite(target, img)
        return target


class GPhotobooth(Photobooth):

    def init_camera(self):
        self.log.debug("Init GPhoto2 camera")
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

    def close_camera(self, camera):
        self.log.debug("close GPhoto2 camera")
        return gp.check_result(gp.gp_camera_exit(camera))

    def take_preview_image(self, camera):
        # self.log.debug("taking preview photo via GPhoto2")
        camera_file = gp.check_result(gp.gp_camera_capture_preview(camera))
        file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
        # decode image
        img = cv2.imdecode(np.fromstring(io.BytesIO(file_data).read(), np.uint8), 1)
        return resize(img, width=self.preview_width)

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
        return target
