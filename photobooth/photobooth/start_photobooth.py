import argparse
from photobooth.photobooth import Photobooth

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-f', '--fullscreen', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('-v', '--verbose', action='store_true', help='Show fullscreen preview', default=False)
    parser.add_argument('--server', action='store_true', help='Start HTTP server', default=False)
    parser.add_argument('--server-only', action='store_true', help='Start only HTTP server without camera', default=False)
    parser.add_argument('--image-dir', type=str, help='image directory', default="~")

    args = parser.parse_args()

    photobooth = Photobooth(image_dir=args.image_dir,
                            fullscreen=args.fullscreen,
                            start_server=args.server,
                            server_only=args.server_only,
                            verbose=args.verbose)
    photobooth.preview()
