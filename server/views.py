import base64
import binascii
import functools
import json
import os
import time
import socket
import re
import calendar
from xml.sax.saxutils import escape

import jsonpickle
import requests

from bs4 import BeautifulSoup
from flask import abort
from flask import render_template
from flask import make_response
from flask import request

from server import app

CACHE_TIMEOUT = 300


def lru_cache(timeout: int, maxsize: int = 128, typed: bool = False):
    def wrapper_cache(func):
        func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)
        func.delta = timeout * 10 ** 9
        func.expiration = time.monotonic_ns() + func.delta

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            if time.monotonic_ns() >= func.expiration:
                func.cache_clear()
                func.expiration = time.monotonic_ns() + func.delta
            return func(*args, **kwargs)

        wrapped_func.cache_info = func.cache_info
        wrapped_func.cache_clear = func.cache_clear
        return wrapped_func
    return wrapper_cache


class Cache():
    def __init__(self, key):
        self.name = key
        self.raw = None
        self.rss = None
        self.fetched = 0
        self.generated = 0

    def set_raw(self, text):
        self.raw = text
        self.fetched = time.time()

    def set_rss(self, text):
        self.rss = text
        self.generated = time.time()

    @property
    def age(self):
        return int(time.time() - self.generated)

    def response(self):
        response = make_response(self.rss)
        response.headers['Content-Type'] = 'application/xml'
        return response

    def load(self):
        try:
            obj = jsonpickle.decode(open(f'/dev/shm/nrfeed_{self.name}.json').read())
        except FileNotFoundError:
            return

        self.rss = obj.rss
        self.raw = obj.raw
        self.generated = obj.generated
        self.fetched = obj.fetched

    def save(self):
        with open(f'/dev/shm/nrfeed_{self.name}.json', 'w') as fd:
            fd.write(jsonpickle.encode(self))
        app.logger.debug(f"[{self.name}] cache saved to disk")


# Application needs to be restarted if feeds.json changes
@functools.lru_cache
def get_feeds():
    return json.load(open(os.path.join(app.root_path, 'feeds.json')))


def rfc2822_date(year, month, day, timestamp, zone):
    year = int(year)
    month = int(month)
    day = int(day)
    dow = calendar.weekday(year, month, day)
    return f"{calendar.day_abbr[dow]}, {day:02d} {calendar.month_abbr[month]} {year} {timestamp} {zone}"


def get_items(data):
    """
    Generates a list of items based on a the json data fetched from the source site
    """
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
        year, month, day = re.match(r'.*/(\d{4})(\d{2})(\d{2}).*\.mp3', audio_url).groups()
        pub_date = rfc2822_date(year, month, day, '12:00:00', 'EST')
        audio_query = {k: v for k, v in (x.split('=', 1) for x in audio_query.split('&'))}
        story_url = segment['storyUrl']
        duration = segment['duration']
        uid = segment['uid']
        values = {
            'title': title,
            'audio_url': audio_url,
            'story_url': story_url,
            'duration': duration,
            'uid': uid,
            'pub_date': pub_date,
        }
        items.append(values)
    return items


# One request per minute per URL. If there is a bug we don't want to kill the remote server.
@lru_cache(60)
def get_source_url(url):
    return requests.get(url, timeout=5)


def find_image(soup, name):
    # See if we can find a logo based on name
    try:
        return soup.findAll('img', {"src": re.compile(f"logos.*{name}")})[0]['src']
    except IndexError:
        pass

    try:
        return soup.findAll('img', {"class": "branding__image-title"})[0]['src']
    except IndexError:
        pass

    raise ValueError

def generate_rss(cache, name, meta):
    soup = BeautifulSoup(cache.raw, features="html.parser")

    play_all = soup.findAll(attrs={'data-play-all': True})
    items = []
    for xml in play_all:
        data = xml.get('data-play-all')
        jdata = json.loads(data)
        items += get_items(jdata)

    title, author = [x.strip() for x in soup.title.text.split(':')]
    if 'title' in meta:
        title = meta['title']

    if 'author' in meta:
        author = meta['author']

    if 'image' in meta:
        image = meta['image']
    else:
        try:
            image = find_image(soup, name)
        except ValueError:
            image = ''

    if 'description' not in meta:
        description = f"Auto-generated by nrfeed. Data sourced from {meta['url']}. Report issues to https://github.com/pyther/nrfeed/issues"
    else:
        description = meta['description']

    url = meta['url']

    values = {
        'title': title,
        'author': author,
        'link': url,
        'description': description,
        'image_url': image,
        'items': items,
        'buildDate': time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(cache.fetched)),
    }

    template = render_template('podcast.xml', **values)
    return template




def get_feed_name(id_):
    feeds = get_feeds()

    if id_ in feeds:
        return id_

    if id_.isdigit():
        for key, value in feeds.items():
            if int(id_) == value['id']:
                return key
    raise ValueError


# Check if cache has expired every 10 seconds, serve from cache otherwise
@lru_cache(1)
def feed(name):
    # Return 404 if feed not in feeds.json
    try:
        meta = get_feeds()[name]
    except ValueError:
        abort(404)

    # Load Cache
    cache = Cache(name)
    cache.load()

    # Retun RSS if cache is valid
    if cache.age <= CACHE_TIMEOUT:
        return cache.response()

    app.logger.debug(f"[{name}] cache expired: {CACHE_TIMEOUT} > {cache.age}")
    # Update cache
    try:
        req = get_source_url(meta['url'])
    except Exception as e:
        app.logger.error(f"[{name}] connection error: {e}")
        abort(503, 'remote server unavailable')
    else:
        if req.ok:
            cache.set_raw(req.text)
            app.logger.debug(f"[{name}] fetched newest data")
        else:
            app.logger.error(f"[{name}] {meta['url']} responded [{req.status_code}]")
            abort(503, 'request to remote server was unsuccessful')

    # Generate RSS XML
    rss = generate_rss(cache, name, meta)
    app.logger.debug(f"[{name}] generated podcast rss")
    cache.set_rss(rss)

    # Write cache, close lock, return response
    cache.save()
    return cache.response()


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', feeds=get_feeds())


@app.route('/podcast/<_id>')
@app.route('/podcast/<_id>.xml')
def podcast(_id):
    try:
        name = get_feed_name(_id)
    except ValueError:
        abort(404)
    return feed(name)
