import argparse
from enum import Enum
from multiprocessing import Process
from photobooth.photobooth import Photobooth, GPhotobooth, Raspibooth


class Camera(Enum):
    raspicam = 'raspicam'
    v4l2 = 'v4l2'
    gphoto2 = 'gphoto2'

    def __str__(self):
        return self.value


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('-v', '--verbose', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('--server', action='store_true', help='Start HTTP server', default=False)
    parser.add_argument('--server-only', action='store_true', help='Start only HTTP server without camera', default=False)
    parser.add_argument('--image-dir', type=str, help='image directory', default="~")
    parser.add_argument('--thumb-width', type=int, help='thumbnail width', default=1280)
    parser.add_argument('--preview-width', type=int, help='preview width', default=1280)
    parser.add_argument('--camera', type=Camera, choices=list(Camera), help='What camera interface?', default=Camera.gphoto2)
    parser.add_argument('--review-time', type=int, help='review time for snapshot in seconds', default=2)


    args = parser.parse_args()

    # set Photobooth class
    if args.camera == Camera.gphoto2:
        Photobooth = GPhotobooth
    elif args.camera == Camera.raspicam:
        Photobooth = Raspibooth

    # create booth if not server only
    if not args.server_only:
        pb = Photobooth(image_dir=args.image_dir,
                        fullscreen=args.fullscreen,
                        thumb_width=args.thumb_width,
                        preview_width=args.preview_width,
                        review_time=args.review_time,
                        verbose=args.verbose)
        pb.preview(block=not args.server)

    # start server
    if args.server:
        print("start server")
        from gevent.pywsgi import WSGIServer
        from photobooth.photoserver import app
        app.config["IMAGE_DIR"] = args.image_dir
        http_server = WSGIServer(('127.0.0.1', 5000), app)
        http_server.serve_forever()

    # cleanup
    if not args.server_only:
        pb.close()
