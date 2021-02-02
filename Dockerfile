FROM python:3.9-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN apk add --no-cache libxml2 libxslt &&\
    apk add --no-cache --virtual .build-deps gcc musl-dev libxml2-dev libxslt-dev &&\
    pip install . gunicorn --no-cache-dir --global-option="build_ext" --global-option="-j5" &&\
    python setup.py install &&\
    apk del .build-deps
CMD ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8152", "server:app"]
