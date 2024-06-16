FROM python:3.12-alpine
WORKDIR /app
ENV PIP_ROOT_USER_ACTION ignore
ENV PYTHONDONTWRITEBYTECODE 1

ADD entrypoint.sh /
ADD server /app/server
ADD setup.py MANIFEST.in requirements.txt /app

RUN apk update && \
    apk add --no-cache libxml2 libxslt
RUN pip install --upgrade pip --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir && \
    pip install gunicorn --no-cache-dir

ENTRYPOINT ["/entrypoint.sh"]
