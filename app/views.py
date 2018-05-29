from . import app

import json
import os
import xml.etree.ElementTree as ET

import flask
from flask import Response
from flask import abort
from flask import url_for
from flask import request
from flask import render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import requests

limiter = Limiter(app, key_func=get_remote_address)
for handler in app.logger.handlers:
    limiter.logger.addHandler(handler)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/debug/programs')
def debug_programs() -> str:
    programs = [f'{k}:{v}' for k, v in get_programs().items()]
    return '\n'.join(programs)

@app.cache.cached(timeout=3600, key_prefix='programs')
def get_programs() -> dict:
    req = requests.get('http://api.npr.org/list?id=3004')
    data = req.content

    root = ET.fromstring(data)
    programs = {elem.attrib['id']: elem.find('title').text for elem in root.findall('item')}

    return programs

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def find_program(name):
    programs = get_programs()

    # Match a program id
    if is_number(name):
        for key, value in programs.items():
            if key == name:
                return (key, value)
        abort(404)

    # Match a program name
    for key, value in programs.items():
        if value.lower().replace(' ', '') == name.lower():
            return (key, value)
    abort(404)

def get_api_key():
    """ Tries to read api key from config file """
    paths = ['./etc/nrfeed.json', '/etc/nrfeed.json']
    for path in paths:
        if os.path.isfile(path):
            config = json.load(open(path, 'r'))
            return config['api_key']

    raise RuntimeError('api key could not be loaded from configuration file')


@app.route('/podcast/<name>')
@limiter.limit("240/day; 50/hour")
@app.cache.cached(timeout=600)
def podcast(name):
    pod_id, pod_name = find_program(name)

    numResults = request.args.get('numResults')
    if not numResults:
        numResults = '50'

    params = {
        'id': pod_id,
        'dateType': 'story',
        'output': 'Podcast',
        'searchType': 'fullContent',
        'numResults': numResults,
        'apiKey': get_api_key()
    }

    url = 'http://api.npr.org/query'
    req = requests.get(url, params=params)

    if req.status_code != 200:
        abort(500)

    data = req.content
    root = ET.fromstring(data)

    namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
    ET.register_namespace('itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')

    # fix title
    root.find('channel/title').text = root.find('channel/title').text.replace('NPR Programs: ', '')

    # update generic image
    image = url_for('static', filename=f'images/{pod_id}.jpg')
    image_url = f'http://{flask.request.host}{image}'
    root.find('channel/image/url').text = image_url
    root.find('channel/itunes:image', namespaces).attrib['href'] = image_url

    xml = ET.tostring(root)
    return Response(xml, mimetype='text/xml')
