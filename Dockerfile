FROM python:3.11-alpine as base
WORKDIR /app
ADD server /app/server
ADD setup.py MANIFEST.in /app
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk add --no-cache libxml2 libxslt
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libxml2-dev libxslt-dev
RUN pip install . gunicorn --no-cache-dir --global-option="build_ext" --global-option="-j5"
#python setup.py install &&\
#apk del .build-deps


FROM python:3.11-alpine
RUN apk add --no-cache libxml2 libxslt
ENV VIRTUAL_ENV=/opt/venv
COPY --from=base $VIRTUAL_ENV $VIRTUAL_ENV
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
CMD ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8152", "server:app"]
