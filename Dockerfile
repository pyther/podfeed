FROM python:3.9-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN pip install gunicorn flask
RUN python setup.py install
RUN mkdir -p /socket/nrfeed
CMD ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8152", "server:app"]
