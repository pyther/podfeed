FROM python:3.8-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN pip install gunicorn flask
RUN python setup.py install
RUN mkdir -p /socket/nrfeed
ENTRYPOINT ["gunicorn", "--log-level=info", "-b", "unix:/socket/nrfeed/gunicorn.sock", "server:app"]
