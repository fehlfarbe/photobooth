import io
import logging
import os
import time
import datetime
from imutils.video import VideoStream, FPS
from imutils import resize
from photobooth.photobooth.tools import GIFCreator
from enum import Enum
from threading import Thread, Event, Lock
from multiprocessing import Process
import signal
import subprocess
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
    info = "info"
    effect_next = "next_effect"
    effect_prev = "prev_effect"
    effect_none = "none_effect"


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
                           pygame.K_p: Action.print_last_photo,
                           pygame.K_i: Action.info,
                           pygame.K_LEFT: Action.effect_prev,
                           pygame.K_RIGHT: Action.effect_next,
                           pygame.K_DOWN: Action.effect_none}
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

            self.pinmap = {21: Action.info,
                           20: Action.interval,
                           19: Action.gif,
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
            GPIO.add_event_detect(k, GPIO.FALLING, bouncetime=1000, callback=self.callback)

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
                 gif_length=5,
                 gif_pause=1.0,
                 input_handler=None,
                 server=True,
                 flip_h=False,
                 flip_v=False):

        # options
        self.image_dir = image_dir
        self.timer_limit = 3
        self.fullscreen = fullscreen
        self.thumb_width = thumb_width
        self.review_time = review_time
        self.gif_length = gif_length
        self.gif_pause = gif_pause
        if input_handler is None:
            input_handler = [KeyboardInput()]
            try:
                input_handler.append(GPIOInput())
            except Exception as e:
                print(e)
                pass
        self.input_handler = input_handler
        self.start_server = server
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.verbose = verbose

        # setup logger
        self.log = logging.getLogger("Photobooth")
        self.log.setLevel(logging.DEBUG if verbose else logging.INFO)

        # pygame window
        self.screen = None
        self.frame_count = 0

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

    def update_window(self, frame, overlays=[]):
        info = pygame.display.Info()
        # frame = resize(frame, height=info.current_h)
        # convert and add image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        frame = pygame.transform.flip(frame, True, False)
        frame = pygame.transform.scale(frame, (info.current_w, info.current_h))
        self.screen.blit(frame, (0, 0))

        # add overlays
        if self.verbose:
            font = pygame.font.SysFont('freesans', 28, bold=True)
            text = "frame #{:d}".format(self.frame_count)
            overlays.append((font.render(text, 1, pygame.Color(255, 255, 255)), 0, info.current_h - 30))
        for overlay, x, y in overlays:
            self.screen.blit(overlay, (x, y))

        # show!
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

    def show_gif(self, buffer, pause=0.3, repeat=5):
        overlays = []
        font = pygame.font.SysFont('freesans', 30, bold=True)
        text = "GIF playback..."
        overlay = font.render(text, 1, pygame.Color(255, 255, 255, 255))
        overlays.append((overlay, 0, 0))
        for i in range(repeat):
            for img in buffer.images:
                self.update_window(img, overlays)
                time.sleep(pause)

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
        pygame.mouse.set_visible(False)
        self.screen = pygame.display.set_mode((0, 0), flags, 32)

        # start preview
        if camera is not None:
            # capture preview image (not saved to camera memory card)
            t0 = time.time()
            timer_active = False
            trigger = False
            last_snap = None
            last_snap_path = None
            # gif
            gif_buffer = None

            info = False
            overlays = []

            # handle signals

            def keyboardInterruptHandler(arg1, arg2):
                self.log.info("Got SIGINT")
                self.event.set()

            signal.signal(signal.SIGINT, keyboardInterruptHandler)

            # counter, fps
            i = 0
            fps = FPS().start()
            # setup thread stop event
            self.event.clear()
            while not self.event.is_set():
                # show last snap
                if last_snap is not None:
                    self.show_snap(last_snap, review_time=self.review_time)
                    last_snap = None
                # self.log.debug('Capturing preview image {:06d}'.format(i))
                img = self.take_preview_image(camera)
                img_preview = img.copy()
                if img is None:
                    self.log.error("Got None image for preview...exit")
                    self.event.set()
                    break
                width, height = img.shape[1], img.shape[0]

                # get action
                action = self.get_action()

                # handle action
                if action is not Action.none:
                    self.log.info("ACTION: {}".format(action))
                    # reset GIF buffer
                    gif_buffer = None
                if action == Action.exit:
                    break
                elif action == Action.photo or trigger:  # SPACE = direct photo
                    # take photo
                    target = self.take_photo(camera, self.path_images)
                    last_snap_path = target
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
                    self.log.info("Start GIF")
                    gif_buffer = GIFCreator(size=self.gif_length, pause=self.gif_pause)
                elif action == Action.print_last_photo:
                    if last_snap_path is not None:
                        self.print_image(last_snap_path)
                        font = pygame.font.SysFont('symbola', 30, bold=True)
                        text = "printing...🖶"
                        overlay = font.render(text, 1, pygame.Color(255, 255, 255))
                        w, h = overlay.get_size()
                        overlays.append((overlay, int(width / 2.0 - w / 2.0), int(height / 2.0 - h / 2.0)))
                    else:
                        self.log.warning("No last snap to print!")
                elif action == Action.info:
                    info = not info
                elif action == Action.effect_next:
                    effect = self.effect_next()
                    self.log.info("effect: {}".format(effect))
                elif action == Action.effect_prev:
                    effect = self.effect_prev()
                    self.log.info("effect: {}".format(effect))
                elif action == Action.effect_none:
                    effect = self.effect_disable()
                    self.log.info("effect: {}".format(effect))
                elif gif_buffer is not None:
                    gif_buffer.update(img)
                    if gif_buffer.is_full():
                        file_path = os.path.join(self.path_images, self.get_image_name("gif"))
                        file_path_thumb = os.path.join(self.path_thumbs, self.get_image_name("gif"))
                        self.log.info("GIF buffer full, save GIF to {}".format(file_path))
                        gif_buffer.save_to(file_path)
                        gif_buffer.save_to(file_path_thumb)
                        self.log.info("Play GIF")
                        self.show_gif(gif_buffer)
                        gif_buffer = None

                # draw timer if active
                if timer_active:
                    time_left = self.timer_limit - (time.time() - t0)
                    if time_left <= 0:
                        time_left = 0
                        trigger = True
                    font_scale = 350 - 50 * (time_left - int(time_left))
                    font = pygame.font.SysFont('freesans', int(font_scale), bold=True)
                    text = "{:d}".format(int(time_left))
                    overlay = font.render(text, 1, pygame.Color(255, 255, 255))
                    w, h = overlay.get_size()
                    overlays.append((overlay, int(width/2.0 - w/2.0), int(height/2.0 - h/2.0)))
                elif gif_buffer is not None:
                    font = pygame.font.SysFont('freesans', 30, bold=True)
                    text = "GIF record..."
                    overlay = font.render(text, 1, pygame.Color(128, 255, 255, 128))
                    overlays.append((overlay, 0, 0))
                elif info:
                    self.log.debug("Show info text")
                    font = pygame.font.SysFont('freesans', 18, bold=True)
                    text = "INFO | 3...2...1...cheeese! | animated GIF | Print last image"
                    overlays.append((font.render(text, 1, pygame.Color(255, 255, 255)), 0, 0))

                if self.verbose:
                    font = pygame.font.SysFont('freesans', 20, bold=True)
                    try:
                        text = "{:.2f} fps".format(float(fps.fps()))
                    except TypeError:
                        text = "0 fps"
                    overlay = font.render(text, 1, pygame.Color(255, 255, 255))
                    w, h = overlay.get_size()
                    overlays.append((overlay, int(width-w), int(height-h)))

                # display image
                self.update_window(img_preview, overlays)
                # clear overlays
                overlays.clear()

                i += 1
                self.frame_count += 1
                fps.update()
                fps.stop()
                self.log.debug("FPS: {}".format(fps.fps()))
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
        if self.flip_h:
            img = cv2.flip(img, 1)
        if self.flip_v:
            img = cv2.flip(img, 0)
        return resize(img, width=self.preview_width)

    def take_photo(self, camera, path):
        img = camera.read()
        if self.flip_h:
            img = cv2.flip(img, 1)
        if self.flip_v:
            img = cv2.flip(img, 0)
        target = os.path.join(path, self.get_image_name())
        cv2.imwrite(target, img)
        return target

    def print_image(self, image_path, fit_to_page=True, printer=None, enhance_for_barcode=True):
        """
        Prints image
        :param image_path: path to image
        :param fit_to_page: scale image to fit page
        :param printer: printer name or None for default printer
        :param enhance_for_barcode: enhance image for barcode printer
        :return: success
        """

        # open image, resize, equalize histogram and add frame
        if enhance_for_barcode:
            img = cv2.imread(image_path)
            img = resize(img, width=500)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.GaussianBlur(img, (5, 5), 0)
            img = cv2.equalizeHist(img)

            # criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            # Z = img.reshape((-1, 1))
            # K = 16
            # ret, label, center = cv2.kmeans(np.float32(Z), K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            #
            # # Now convert back into uint8, and make original image
            # center = np.uint8(center)
            # res = center[label.flatten()]
            # img = res.reshape((img.shape))

            # add border
            h, w = img.shape
            img = cv2.rectangle(img, (0, 0), (w, h), (0, 0, 0), 10)
            cv2.imwrite("/tmp/print.jpg", img)
            image_path = "/tmp/print.jpg"
            # return

        cmd = ["lpr"]
        if printer is not None:
            cmd.extend(["-d", printer])
        if fit_to_page:
            cmd.extend(["-o", "fit-to-page"])
        cmd.append(image_path)
        p = subprocess.Popen(cmd)
        return True

    def get_image_name(self, file_type="jpg"):
        return "{}.{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), file_type)

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

    def effect_next(self):
        return None

    def effect_prev(self):
        return None

    def effect_disable(self):
        return "off"


class Raspibooth(Photobooth):

    def __init__(self, *args, **kwargs):
        super(Raspibooth, self).__init__(*args, **kwargs)
        # self.rawCapture = None
        # self.rawCapture_preview = None
        # self.cap = None
        # self.cap_preview = None
        # self.stream = None
        self.lock = Lock()

        self.img = None
        self.camera = None

        self.run_camera = Event()
        self.camera_thread = None

        self.effects = ("none", "negative", "solarize", "sketch",
                        "emboss", "oilpaint", "pastel", "watercolor", "film",
                        "colorswap", "washedout", "posterise", "cartoon")
        self.current_effect = 0

    def init_camera(self):
        # self.log.debug("init camera")
        # vs = VideoStream(usePiCamera=True, resolution=(1920, 1088))
        # vs.start()
        # time.sleep(2.0)
        import picamera
        from picamera.array import PiRGBArray

        self.log.info("Open PiCamera...")
        # self.camera = VideoStream(resolution=(800, 480), framerate=30, usePiCamera=True)
        # self.camera.start()
        # time.sleep(2.0)
        camera = picamera.PiCamera(resolution=(1920, 1080), framerate=20)
        camera.hflip = self.flip_h
        camera.vflip = self.flip_v
        camera.drc_strength = "medium"
        self.camera = camera
        self.log.info(camera)
        # camera.start_preview()
        time.sleep(2.0)
        # self.rawCapture = PiRGBArray(camera)
        self.camera_thread = Thread(target=self.run)
        self.camera_thread.start()
        return self.camera

    def close_camera(self, camera):
        self.log.info("close camera")
        self.run_camera.set()
        self.camera_thread.join()
        # self.stream.close()
        # self.rawCapture_preview.close()
        camera.close()

    def run(self):
        from picamera.array import PiRGBArray
        i = 0
        rawCapture_preview = PiRGBArray(self.camera, size=(800, 480))
        stream = self.camera.capture_continuous(rawCapture_preview,
                                                format="bgr",
                                                resize=(800, 480),
                                                use_video_port=True)
        for frame in stream:
            self.log.debug("got frame {:d}".format(i))
            self.img = frame.array.copy()

            rawCapture_preview.truncate(0)
            i += 1

            if self.run_camera.is_set():
                self.log.debug("close camera preview")
                break
        stream.close()

    def take_preview_image(self, camera):
        while self.img is None:
            self.log.warning("Waiting for preview image...")
            time.sleep(0.1)
        #with self.lock:
        return self.img
        # img = self.img.copy()

        # img = np.empty((1088, 1920, 3), dtype=np.uint8)
        # camera.capture(img, 'bgr', use_video_port=True, splitter_port=2)
        # return resize(img, width=self.preview_width)

        # return img

    def take_photo(self, camera, path):
        # while self.img is None:
        #     time.sleep(0.1)
        # self.rawCapture.truncate(0)
        img = np.empty((1088, 1920, 3), dtype=np.uint8)
        camera.capture(img, 'bgr', use_video_port=True, splitter_port=1)
        # img = next(self.cap).array
        target = os.path.join(path, self.get_image_name())
        cv2.imwrite(target, img)
        return target

    def effect_next(self):
        self.current_effect = (self.current_effect + 1) % len(self.effects)
        self.camera.image_effect = self.effects[self.current_effect]
        return self.effects[self.current_effect]

    def effect_prev(self):
        self.current_effect = (self.current_effect - 1) % len(self.effects)
        self.camera.image_effect = self.effects[self.current_effect]
        return self.effects[self.current_effect]

    def effect_disable(self):
        self.current_effect = 0
        self.camera.image_effect = self.effects[self.current_effect]


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
