# nrfeed
podcast feeds for NPR shows

A simple flask app that uses the NPR API to generate rss feeds for All Things
Considered, Morning Edition, Weekend Edition Saturady and Weekend Edition
Sunday.

## Purpose

The podcast feeds that NPR provides for their news programs (All Things
Considered, Morning Edition, Weekend Edition) only contain 15 results.
Typically more than 15 audio segments are published per day. Additionally, the
same generic podcast image is used for each of these feeds, making it hard to
identify the podcast in a podcast app.

## How It Works

We use the public NPR API to request a "Podcast" feed for each program. The API
allows us to specify how many episodes to return, currently this is set to 50
which should provide 2-3 days worth of material for All Things Considered and
Morning Edition.

The following modification are made to feed returned by the API

   - Podcast title: remove phrase "NPR Programs: " from title
   - Podcast image: replace generic npr image with show specific image


## Testing

 - install python-flask and python-flask-cache `$ yum install python-flask python-flask-cache`
 - run `$ python wsgi.py`
 - open 'http://localhost:5000'

## Screenshots

### Firefox
![Firefox](/img/firefox.png?raw=true)

### Pocket Cast (Android)
![Pocket Cast](/img/pocketcast.png?raw=true)

# Testing / Development
To get going and start the development webserver run the following commands
```
$ virtualenv-3 venv
$ source ./venv/bin/activate
$ python setup.py develop
$ mkdir etc
$ echo '{"api_key": "PUT_API_KEY_HERE"}' > ./etc/nrfeed.json
$ python run.py
```

## Installation
Flask application can be deployed and number of ways. With that said, below are
the steps I used.

```
$ useradd -r webapp
$ git clone https://github.com/pyther/nrfeed.git
$ cd nrfeed
$ mkdir /opt/nrfeed
$ virtualenv-3 /opt/nrfeed
$ source /opt/nrfeed/bin/activate
$ python setup.py install
$ cp systemd/gunicorn.service /etc/systemd/system/gunicorn.service
$ cp systemd/gunicorn.tmpfile /etc/tmpfiles.d/gunicorn.conf
$ echo '{"api_key": "PUT_API_KEY_HERE"}' > /opt/nrfeed/etc/nrfeed.json
$ systemd-tmpfiles --create /etc/tmpfiles.d/gunicorn.conf
$ systemctl enable gunicorn.service
$ systemctl start gunicorn.service
$ cp systemd/nginx.conf /etc/nginx/conf.d/npr.conf
```
