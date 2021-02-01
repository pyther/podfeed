FROM python:3.9-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN pip install --no-cache-dir gunicorn flask
RUN apk add --no-cache libxml2 libxslt &&\
    apk add --no-cache --virtual .build-deps gcc musl-dev libxml2-dev libxslt-dev &&\
    python setup.py install &&\
    apk del .build-deps
CMD ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8152", "server:app"]
