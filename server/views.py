from server import app

import base64
import binascii
import json
import os
import time
import socket
import re
import calendar

from xml.sax.saxutils import escape

import requests

from bs4 import BeautifulSoup

import flask
from flask import abort
from flask import url_for
from flask import render_template
from flask import make_response
#from flask import current_app as app

from flask_limiter import Limiter
from flask_limiter.util import get_ipaddr

import pickledb

CACHE_TIMEOUT = 600
#RETRY_LIMIT = 60
RETRY_LIMIT = 5

limiter = Limiter(app, key_func=get_ipaddr, default_limits=['30/minute', '120/hour', '1440/day'])
for handler in app.logger.handlers:
    limiter.logger.addHandler(handler)

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

def rfc2822_date(year, month, day, time, zone):
    year = int(year)
    month = int(month)
    day = int(day)
    dow = calendar.weekday(year, month, day)
    return f"{calendar.day_abbr[dow]}, {day:02d} {calendar.month_abbr[month]} {year} {time} {zone}"

def generate_items(data):
    items = []
    for segment in data['audioData']:
        title = escape(segment['title'])
        audio_url = segment['audioUrl']
        if not audio_url.startswith('http'):
            try:
                audio_url = base64.b64decode(audio_url).decode('utf-8')
            except binascii.Error:
                continue
        audio_url, audio_query = audio_url.split('?', 1)
        year, month, day = re.match('.*/(\d{4})(\d{2})(\d{2}).*\.mp3', audio_url).groups()
        pub_date = rfc2822_date(year, month, day, '12:00:00', 'EST')
        audio_query = {k:v for k, v in (x.split('=', 1) for x in audio_query.split('&'))}
        audio_size = audio_query['size']
        story_url = segment['storyUrl']
        duration = segment['duration']
        uid = segment['uid']
        values = {
            'title': title,
            'audio_url': audio_url,
            'audio_size': audio_size,
            'story_url': story_url,
            'duration': duration,
            'uid': uid,
            'pub_date': pub_date,
        }
        items.append(values)
    return items

def generate_feed(url, title, author, description, image):
    req = requests.get(url, timeout=5)
    req.raise_for_status()
    soup = BeautifulSoup(req.text, features="html.parser")

    play_all = soup.findAll(attrs={'data-play-all': True})
    items = []
    for xml in play_all:
        data = xml.get('data-play-all')
        jdata = json.loads(data)
        items += generate_items(jdata)

    values = {
        'title': title,
        'author': author,
        'link': url,
        'description': description,
        'image_url': image,
        'items': items,
    }

    template = render_template('podcast.xml', **values)
    return template

def load_cache_db(name):
    return pickledb.load(f'/tmp/nrfeed_{name}.json', False, False)

def is_cache_expired(name):

    db = load_cache_db(name)
    if not db.exists('generated'):
        return True

    # Has cached expired?
    age = int(time.time()) - db.get('generated')
    if age > CACHE_TIMEOUT:
        app.logger.debug('[%s] cache expired; %d > %d', name, age, CACHE_TIMEOUT)
        return True

    app.logger.debug('[%s] cache age %d, expiration %d', name, age, CACHE_TIMEOUT)
    return False

def serve_cache(name):

    db = load_cache_db(name)
    if not db.exists('xml'):
        app.logger.error('exception occured while trying to serve from cache: %s')
        abort(500, 'No cached data and connection error to NPR.')

    app.logger.debug('[%s] served from cache', name)
    response = make_response(db.get('xml'))
    response.headers['Content-Type'] = 'application/xml'
    return response

def serve_rss(name):

    feeds = json.load(open(os.path.join(app.root_path, 'feeds.json')))
    data = feeds[name]
    image = url_for('static', filename=f"images/{name}.jpg")
    image_url = f'http://{flask.request.host}{image}'

    app.logger.debug('[%s] generating podcast rss', name)
    xml = generate_feed(data['url'], data['title'], data['author'], data['description'], image_url)
    app.logger.info('[%s] rss generated', name)

    # Update db cache
    app.logger.debug('[%s] updating cache', name)
    db = load_cache_db(name)
    db.set('xml', xml)
    db.set('generated', int(time.time()))
    db.dump()
    app.logger.info('[%s] cache updated', name)

    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response

def get_feed(name):
    # Cache is not expired, serve cached version
    if not is_cache_expired(name):
        return serve_cache(name)

    # Cache is expired, but we attempted to build an rss feed and it presumably failed
    # Rate limit per feed, so we don't send too many requests to the remote server
    db = load_cache_db(name)
    last_failed = db.get('failed')
    if last_failed:
        diff = int(time.time()) - last_failed
        if diff <= RETRY_LIMIT:
            app.logger.debug('[%s] serving from cache, last failed build was %d seconds ago', name, diff)
            return serve_cache(name)

    # Try to build a new rss feed. If we can't get a lock, there is probably
    # another worker updating the cache, so just serve from cache.
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0nrfeed_'+name)
    except socket.error:
        # another instance is trying to update the cache, serve cache or throw a 500
        app.logger.info('unable to secure lock, serving cache copied of the content')
        return serve_cache(name)

    # we got a lock, now lets refresh the rss feed
    try:
        response = serve_rss(name)
    except Exception as e:
        app.logger.info('[%s] failed to generate rss. Exception %s', name, e)
        response = serve_cache(name)
        db = load_cache_db(name)
        db.set(f"failed", int(time.time()))
        db.dump()
        raise e
    finally:
        lock_socket.close()

    return response

#@limiter.limit("240/day; 30/hour")
@app.route('/podcast/all-things-considered')
@app.route('/podcast/2')
def podcast_all_things_considered():
    return get_feed('all-things-considered')

#@limiter.limit("240/day; 30/hour")
@app.route('/podcast/morning-edition')
@app.route('/podcast/3')
def podcast_morning_edition():
    return get_feed('morning-edition')

@app.route('/podcast/weekend-edition-saturday')
@app.route('/podcast/7')
def podcast_weekend_edition_saturday():
    return get_feed('weekend-edition-saturday')

@app.route('/podcast/weekend-edition-sunday')
@app.route('/podcast/10')
def podcast_weekend_edition_sunday():
    return get_feed('weekend-edition-sunday')
