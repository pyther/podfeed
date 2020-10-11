# nrfeed
Auto-generates RSS Podcast Feeds

A simple flask app that extracts data from a remote source and generate an
RSS Podcast feed that can be used by various podcasting applications.

# Testing / Development
To get going and start the development webserver run the following commands
```
$ python -m venv venv
$ source ./venv/bin/activate
$ python setup.py develop
$ python run.py
```

# Production
There are various guides on setting up flasks apps in production.

If you use Docker, see the included Dockerfile.
Or use the published build: ```docker run -d --restart always -p 8010:8000 --name nrfeed mgyurgyik/nrfeed:latest```
