from app import app

from settings import APP_CACHE, APP_STATIC, APP_ROOT
from settings import API_KEY, SERVER_NAME

from flask import url_for
from flask import request
from flask import abort
from flask import Response
from flask import render_template

import requests
import xml.etree.ElementTree as ET
import os
import datetime
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


def is_older_than(fname, seconds):
    stat = os.stat(os.path.join(APP_CACHE, 'programs.xml'))
    st_mtime = stat.st_mtime

    now = datetime.datetime.now()
    mtime = datetime.datetime.fromtimestamp(st_mtime)

    if (now - mtime) > datetime.timedelta(seconds=seconds):
        return True

    return False

def update_program_data():
    req = requests.get('http://api.npr.org/list?id=3004')
    data = req.content

    with open(os.path.join(APP_CACHE, 'programs.xml'), 'w') as fd:
        fd.write(data)

    return

def get_programs():

    cache_file = './cache/programs.xml'
    if (os.path.isfile(cache_file) and
        is_older_than(cache_file, 86400)):
            update_program_data()
    else:
        update_program_data()

    tree = ET.parse(os.path.join(APP_CACHE, 'programs.xml'))
    root = tree.getroot()
    #root = ET.fromstring(data)
    progs = {elem.attrib['id']: elem.find('title').text for elem in root.findall('item')}

    return progs
