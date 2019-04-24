import argparse
from enum import Enum
from multiprocessing import Process
from photobooth.photobooth import Photobooth, GPhotobooth


class Camera(Enum):
    raspicam = 'raspicam'
    v4l2 = 'v4l2'
    gphoto2 = 'gphoto2'

    def __str__(self):
        return self.value


def run_server(image_dir):
    from photobooth.photoserver import app
    app.config["IMAGE_DIR"] = image_dir
    app.run("0.0.0.0", debug=True, threaded=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('-v', '--verbose', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('--server', action='store_true', help='Start HTTP server', default=False)
    parser.add_argument('--server-only', action='store_true', help='Start only HTTP server without camera', default=False)
    parser.add_argument('--image-dir', type=str, help='image directory', default="~")
    parser.add_argument('--thumb-width', type=int, help='thumbnail width', default=1280)
    parser.add_argument('--camera', type=Camera, choices=list(Camera), help='What camera interface?', default=Camera.gphoto2)

    args = parser.parse_args()

    if args.camera == Camera.gphoto2:
        Photobooth = GPhotobooth

    pb = Photobooth(image_dir=args.image_dir,
                    fullscreen=args.fullscreen,
                    start_server=args.server,
                    server_only=args.server_only,
                    thumb_width=args.thumb_width,
                    verbose=args.verbose)
    pb.preview(block=not args.server)

    # start server
    if args.server:
        run_server(args.image_dir)
        # server_thread = Process(target=run_server, args=(args.image_dir,))
        # server_thread.start()

    pb.close()
