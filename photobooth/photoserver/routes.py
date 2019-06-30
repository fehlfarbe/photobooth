from flask import render_template, send_from_directory, request, redirect, url_for
from . import app
from .pagination import Pagination
import os
import glob


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)


app.jinja_env.globals['url_for_other_page'] = url_for_other_page


@app.route('/', defaults={'page': 1})
@app.route('/page/<int:page>')
def index(page):
    per_page = 10
    images = []
    img_dir = app.config.get("IMAGE_DIR", None)

    # app.logger.info(app.config["IMAGE_DIR"])
    if img_dir is not None and os.path.exists(img_dir):
        types = ("*.gif", "*.jpg", "*.jpeg")
        for t in types:
            for img in glob.glob(os.path.join(app.config["IMAGE_DIR"], "thumbs", t)):
                images.append(os.path.basename(img))
    images = sorted(images, reverse=True)
    total_count = len(images)
    start = (page-1) * per_page
    end = min(start + per_page, total_count -1)
    images = images[start:end]
    pagination = Pagination(page, per_page, total_count)
    # app.logger.info(images)
    return render_template('index.html', images=images, pagination=pagination)


@app.route('/image/<path:path>')
def send_image(path):
    return send_from_directory(os.path.join(app.config.get("IMAGE_DIR", "."), "images"), path)


@app.route('/thumb/<path:path>')
def send_thumb(path):
    return send_from_directory(os.path.join(app.config.get("IMAGE_DIR", "."), "thumbs"), path)


@app.errorhandler(404)
def page_not_found(e):
    return index(1)
