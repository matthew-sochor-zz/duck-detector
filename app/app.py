import base64
import os
import random
import subprocess
import sqlite3
import uuid

import logging as log

import numpy as np

from flask import Flask, redirect, render_template, request, url_for
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename

from PIL import Image as pil_image

from .models import Pics
from .sqlite_queue import SqliteQueue
from .score_fish_pic import predict

log.basicConfig(level=log.DEBUG)


# Flask extensions
bootstrap = Bootstrap()


app = Flask(__name__)


# Initialize flask extensions
bootstrap.init_app(app)


log.basicConfig(level=log.DEBUG)


# env vars for tmp purposes
class Config(object):
    # DEBUG = False
    # TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY',
                                'superSecretDoNotUseOnOpenWeb')


# init config
app.config.from_object(Config)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # TODO: add data validation step
        if True:
            log.debug('data:')
            log.debug(request.data)
            log.debug('files:')
            log.debug(request.files)
            pic_file = request.files['pic-input']
            # TODO: path should be updated before production
            dump_path = os.path.join('data', 'pics')
            dump_path_sm = os.path.join('data', 'pics_sm')
            log.debug('dump_path:')
            log.debug(os.listdir(dump_path))

            pic_ext = 'jpg'

            # reading into PIL
            log.debug('Reading PIL: %s', pic_file.filename)
            img = pil_image.open(pic_file)

            # get a random uuid to use for filename
            pic_uuid = uuid.uuid4()

            pic_name = '{}.{}'.format(pic_uuid, pic_ext)

            pic_path = os.path.join(dump_path, pic_name)

            pic_path_sm = os.path.join(dump_path_sm, pic_name)

            log.debug('Saving: %s', pic_path)
            log.debug('Saving: %s', pic_path_sm)

            # TODO: resize and convert to jpg on save
            # pic_file.save(pic_path)
            img.save(pic_path)
            # save thumbnail version
            mc = 300
            if img.size[0] > img.size[1]:
                wh_tuple = (mc, img.size[1] * mc // img.size[0])
            else:
                wh_tuple = (img.size[0] * mc // img.size[1], mc)

            img_sm = img.resize(wh_tuple)
            img_sm.save(pic_path_sm)

            img_path = os.path.abspath(pic_path)
            img_path_sm = os.path.abspath(pic_path_sm)

            # add submission to database
            # TODO: make an ENV var
            pic_db = Pics('data/dbs/pics.db')
            pic_id = pic_db.append({'img_path': img_path, 'img_path_sm': img_path_sm})

            predict(pic_id, pic_path)

            # push to scoring queue
            # TODO: make queue path a global in ENV
            log.debug('Push queue: %s', pic_path)
            pic_queue = SqliteQueue('data/queues/pic_queue.db')
            pic_queue.append((pic_id, img_path))

            return redirect(url_for('loading_splash',
                                    pic_id=pic_id))

    # TODO: refactor this block
    # art for photo upload page
    art_sel = 'CameraIconSmall.png'
    art_url = url_for('static',
                      filename='{}/{}'.format('images',
                                              art_sel))

    # if not a post request return html
    return render_template('upload.html', art_url=art_url)


def get_pic_dict(pic_id):
    # function is used to "gin up" the real/fake result data
    # return None if scoring is not finished
    # else return the entire pic_dict dump

    # TODO: refactor to ENV global
    pic_db = Pics('data/dbs/pics.db')
    pic_dict = pic_db.get(pic_id)
    log.debug('pic_dict: %s', pic_dict)

    species_pred = pic_dict.get('species_pred')

    if not species_pred:
        # TODO: refactor this to get a true get dict fxn or rename
        # return null data until scoring job finishes
        return pic_dict

    else:

        confidence = np.round(np.max(pic_dict.get('y_pred')), 2) * 100

        results = {'species': species_pred,
                   'confidence': confidence}

        pic_dict['results'] = results

        # TODO: refactor this to seperate function
        # save the calcs from this function to DB
        pic_db.replace(pic_id, pic_dict)
        log.info('Commited to DB: %s', pic_dict)

        return pic_dict


def _get_if_exist(data, key):
    if key in data:
        return data[key]
    return None

@app.route('/loading_splash/<int:pic_id>')
def loading_splash(pic_id):
    pic_dict = get_pic_dict(pic_id)
    return redirect(url_for('submission_results',
                                pic_id=pic_id))


@app.route('/cdn_pic/<int:pic_id>')
@app.route('/cdn_pic/<int:pic_id>.jpg')
def cdn_pic(pic_id):
    pic_dict = get_pic_dict(pic_id)
    log.debug('pic_dict: %s', pic_dict)

    img_path = pic_dict['img_path']

    with open(img_path, 'rb') as f:
        pic_file = f.read()

    return pic_file, 200, {'Content-Type': 'image/jpg'}


@app.route('/cdn_pic_sm/<int:pic_id>')
@app.route('/cdn_pic_sm/<int:pic_id>.jpg')
def cdn_pic_sm(pic_id):
    pic_dict = get_pic_dict(pic_id)
    log.debug('pic_dict: %s', pic_dict)

    img_path = pic_dict['img_path_sm']

    with open(img_path, 'rb') as f:
        pic_file = f.read()

    return pic_file, 200, {'Content-Type': 'image/jpg'}



@app.route('/submission_results/<int:pic_id>')
def submission_results(pic_id):
    pic_dict = get_pic_dict(pic_id)

    # redirect if user inputs non existant key
    if not pic_dict:
        return redirect(url_for('index'))

    results = pic_dict['results']

    # TODO: refactor this into lookup functions
    # based on state rules database(s).

    results_heading_dict = {
        'human': 'This is (probably) a human',
        'duck': 'Its a damned duck.  Eww.',
        'pooduck': 'Poo + duck = '
    }

    species_pred = results['species']
    confidence = results['confidence']

    # the heading is the bold message displayed to user
    results_heading = results_heading_dict[species_pred]

    return render_template('submission_results.html',
                           results_heading=results_heading,
                           species_pred=species_pred,
                           confidence=confidence,
                           pic_id=pic_id)
