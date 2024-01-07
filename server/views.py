import json
import os
import time
import datetime
import pytz
from xml.sax.saxutils import escape
from wsgiref.handlers import format_date_time
import cachetools.func
import diskcache

import requests
import podgen

from flask import abort
from flask import render_template
from flask import make_response
from flask import request

from server.parser.npr import NprParser
from server import app


CACHE_TIMEOUT = 300


# Application needs to be restarted if feeds.json changes
@cachetools.func.lru_cache
def get_feeds():
    return json.load(open(os.path.join(app.root_path, 'feeds.json')))


@cachetools.func.lru_cache
def get_feed_name(id_):
    feeds = get_feeds()

    if id_ in feeds:
        return id_

    if id_.isdigit():
        for key, value in feeds.items():
            if int(id_) == value['id']:
                return key
    raise ValueError


# One request per minute per URL. If there is a bug we don't want to kill the remote server.
@cachetools.func.ttl_cache(maxsize=128, ttl=60)
def get_url(url):
    return requests.get(url, timeout=5)


def generate_rss(text, name, meta):
    if meta['parser'] == 'npr':
        publication_time = meta.get('publication_time', None)
        if publication_time:
            data = NprParser(text, name, publication_time=publication_time)
        else:
            data = NprParser(text, name)
    else:
        raise ValueError(f"unknown parser type {meta['parser']}")

    episodes = []
    for item in data.episodes:
        e = podgen.Episode()
        e.id = escape(item.id)
        e.title = escape(item.title)
        e.media = podgen.Media(item.media_url, item.media_size, duration=datetime.timedelta(seconds=item.media_duration))
        e.publication_date = item.publication_date
        e.link = item.link
        episodes.append(e)

    if 'title' in meta:
        title = meta['title']
    else:
        title = getattr(data, 'title')

    if 'author' in meta:
        author = meta['author']
    else:
        author = getattr(data, 'author', None)

    if 'image' in meta:
        image = meta['image']
    else:
        image = getattr(data, 'image', None)

    if 'description' in meta:
        description = meta['description']
    else:
        description = f"Auto-generated by podfeed. Data sourced from {meta['url']}. Report issues to https://github.com/pyther/podfeed/issues"

    category = meta.get('category', None)
    url = meta.get('url', None)

    podcast = podgen.Podcast()
    podcast.name = escape(title)
    podcast.description = escape(description)
    if url:
        podcast.website = url
    if category:
        podcast.category = podgen.Category(category[0], category[1])
    podcast.language = "en-US"
    if author:
        podcast.authors = [podgen.Person(author, None)]
    if image:
        podcast.image = image
    podcast.explicit = False
    podcast.last_updated = pytz.utc.localize(datetime.datetime.now())
    podcast.generator = "pyther/podfeed"
    podcast.episodes = episodes
    podcast.publication_date = False

    return podcast.rss_str()


# Check if cache has expired every 10 seconds, serve from cache otherwise
@cachetools.func.ttl_cache(maxsize=128, ttl=1)
def feed(name):
    meta = get_feeds()[name]

    # Load Cache
    cache = diskcache.Cache('/tmp/podfeed')

    # cache is expired if item dosen't exist
    if name not in cache:
        # Update cache
        try:
            req = get_url(meta['url'])
        except Exception as e:
            app.logger.error(f"connection error: {e}")
            abort(503, 'remote server unavailable')
        else:
            if req.ok:
                cache.set(name, req.text, expire=CACHE_TIMEOUT)
                app.logger.info(f"cache updated for {name}")
            else:
                app.logger.error(f"status code {req.status_code} from {meta['url']}")
                abort(503, 'request to remote server was unsuccessful')

    # Get expiration time
    text, expire_time = cache.get(name, expire_time=True)
    expire_time = int(expire_time)
    cache.close()

    # Generate RSS XML
    rss = generate_rss(text, name, meta)
    app.logger.info(f"generated rss for {name}")

    response = make_response(rss)
    response.headers['Content-Type'] = 'application/xml'
    if expire_time:
        max_age = int(expire_time - time.time())
        response.headers['Expires'] = format_date_time(expire_time)
        response.headers['Cache-Control'] = f"public, max-age={max_age}, stale-if-error=43200"
    return response


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
    response = feed(name)
    return response
