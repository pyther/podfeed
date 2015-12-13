from app import app

from settings import APP_CACHE, APP_STATIC, APP_ROOT
from settings import API_KEY, SERVER_NAME

from flask import Response
from flask import abort
from flask import url_for
from flask import request
from flask import render_template

import requests
import xml.etree.ElementTree as ET
import os
import urllib

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/debug/programs')
def debug_programs():
    output = ''
    for k,v in get_programs().iteritems():
        output += '{0}:{1}\n'.format(k, v)
    return output

@app.route('/podcast/<program>')
@app.cache.cached(timeout=120)
def podcast(program):

    # check program requested is valid
    try:
        pid, pname = program_match(program)
    except TypeError:
        abort(404)

    numResults = request.args.get('numResults')
    if not numResults:
        numResults = '50'

    params = {
        'id':pid,
        'dateType':'story',
        'output':'Podcast',
        'searchType':'fullContent',
        'numResults':numResults,
        'apiKey':API_KEY
    }

    url = 'http://api.npr.org/query?{0}'.format(urllib.urlencode(params))
    req = requests.get(url)

    if req.status_code != 200:
        abort(req.status_code)

    data = req.content
    root = ET.fromstring(data)

    ET.register_namespace('itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')

    namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

    # fix title
    root.find('channel/title').text = root.find('channel/title').text.replace('NPR Programs: ', '')

    # update generic image
    if os.path.isfile(os.path.join(APP_STATIC, 'images/{0}.jpg'.format(pid))):
        new_image = 'http://{0}{1}'.format(SERVER_NAME, url_for('static', filename='images/{0}.jpg'.format(pid)))
        root.find('channel/image/url').text = new_image
        root.find('channel/itunes:image', namespaces).attrib['href'] = new_image

    xml = ET.tostring(root)
    return Response(xml, mimetype='text/xml')

def program_match(name):
    programs = get_programs()

    pid = None
    for key,value in programs.iteritems():
        if name == key:
            return (key, value)
        elif name == value:
            return (key, value)

        alt_value = value.replace(' ', '').lower()

        if name.lower() == alt_value:
            return (key, value)

    return None

@app.cache.cached(timeout=3600, key_prefix='programs')
def get_programs():
    req = requests.get('http://api.npr.org/list?id=3004')
    data = req.content

    root = ET.fromstring(data)
    progs = {elem.attrib['id']: elem.find('title').text for elem in root.findall('item')}

    return progs

