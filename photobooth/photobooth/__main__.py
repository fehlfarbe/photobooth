import argparse
import time
from photobooth.photobooth import Photobooth, Camera


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose', default=False)
    parser.add_argument('--server', action='store_true', help='Start HTTP server', default=False)
    parser.add_argument('--server-only', action='store_true', help='Start only HTTP server without camera', default=False)
    parser.add_argument('--hflip', action='store_true', help='horizontal flip', default=False)
    parser.add_argument('--vflip', action='store_true', help='vertical flip', default=False)
    parser.add_argument('--image-dir', type=str, help='image directory', default="~")
    parser.add_argument('--thumb-width', type=int, help='thumbnail width', default=1280)
    parser.add_argument('--camera', type=Camera, choices=list(Camera), help='What camera interface?', default=Camera.gphoto2)
    parser.add_argument('--review-time', type=int, help='review time for snapshot in seconds', default=2)

    args = parser.parse_args()

    # create photobooth
    pb = Photobooth(image_dir=args.image_dir,
                    fullscreen=args.fullscreen,
                    thumb_width=args.thumb_width,
                    review_time=args.review_time,
                    verbose=args.verbose,
                    server=args.server,
                    flip_h=args.hflip,
                    flip_v=args.vflip,
                    cam_type=args.camera)
    if not args.server_only:
        pb.preview(block=True)
    else:
        # pb.run_server()
        while True:
            try:
                time.sleep(3)
            except KeyboardInterrupt as e:
                break

    # cleanup
    pb.close()
