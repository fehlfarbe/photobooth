from flask import render_template, send_from_directory
from . import app
import os
import glob


@app.route('/')
@app.route('/index')
def index():
    images = []
    img_dir = app.config.get("IMAGE_DIR", None)

    # app.logger.info(app.config["IMAGE_DIR"])
    if img_dir is not None and os.path.exists(img_dir):
        types = ("*.gif", "*.jpg", "*.jpeg")
        for t in types:
            for img in glob.glob(os.path.join(app.config["IMAGE_DIR"], "thumbs", t)):
                images.append(os.path.basename(img))
    images = sorted(images, reverse=True)
    # app.logger.info(images)
    return render_template('index.html', images=images)


@app.route('/image/<path:path>')
def send_image(path):
    return send_from_directory(os.path.join(app.config.get("IMAGE_DIR", "."), "images"), path)


@app.route('/thumb/<path:path>')
def send_thumb(path):
    return send_from_directory(os.path.join(app.config.get("IMAGE_DIR", "."), "thumbs"), path)

